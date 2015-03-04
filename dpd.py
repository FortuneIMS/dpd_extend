# -*- coding: utf-8 -*-

from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.tools as tools
from openerp.addons.dpd import dpd_request
import datetime
import time
from openerp.addons.google_cloud_printing import gcp
import openerp.addons.decimal_precision as dp

class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'shipping_customer': fields.boolean('Shipping Customer'),
    }
    _defaults = {
    }
res_partner()

class dpd_shipping(osv.osv):
    _inherit = 'dpd.shipping'

    _columns = {
        'sending_with_us': fields.boolean('Sending with us'),
        'weight_amount': fields.float('Price', digits_compute=dp.get_precision('Stock Weight')),
        'weight_product_id': fields.many2one('product.product', 'Weight Product'),
        'invoice_ids': fields.one2many('account.invoice','dpd_shipping_id', 'Invoice(s)'),
        'invoice_to': fields.selection([('customer','Customer'),('sender','Sender')], 'Invoice To'),
        'type': fields.boolean('Is Express Packaging for DPD ?')
    }
    _defaults = {'invoice_to': lambda *a: 'sender',
                 'type':lambda *a:True
                 }
    def get_user_signature(self, cr, uid, ids, context={}):
        user_obj = self.pool.get('res.users').browse(cr,uid,uid)
        res = []
        if user_obj.signature:
            res = user_obj.signature.split('\n')
        return res
    
    def action_send_tracking_id_mail(self, cr, uid, ids, context=None):
        '''
        This function opens a window to compose an email, with the edi sale template message loaded by default
        '''
        assert len(ids) == 1, 'This option should only be used for a single id at a time.'
        ir_model_data = self.pool.get('ir.model.data')
        try:
            template_id = ir_model_data.get_object_reference(cr, uid, 'dpd', 'email_template_dpd_tracking_number')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False 
        ctx = dict(context)
        ctx.update({
            'default_model': 'dpd.shipping',
            'default_res_id': ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }
        
    def calc_weight(self, cr, uid, ids, context=None):
        uom_obj = self.pool.get('product.uom')
        for shipping in self.browse(cr, uid, ids, context=context):
            total_weight = 0.00

            for picking in shipping.delivery_order_ids:
                for move in picking.move_lines:
                    total_weight += move and move.product_id and move.product_id.weight_net or move.weight or 0.0
            self.write(cr, uid, [shipping.id], {'weight' : total_weight})
            self.calc_weight_amount(cr, uid, [shipping.id], context)                  
        return True
    
    def calc_weight_amount2(self, cr, uid, ids, context=None):
        if context is None: context = {}
        for picking in self.browse(cr, uid, ids, context=context):
            if picking.weight <= 0:
                weight_amount = 0.0
            else:
                #19% VAT SHOULD BE ADDED
                if picking.weight <= 3:
                    weight_amount = 2.80
                elif picking.weight <= 15:
                    weight_amount = 3.20
                elif picking.weight <= 31.5:
                    weight_amount = 3.60
                else:
                    weight_amount = 0.0
        return self.write(cr, uid, ids, {'weight_amount': weight_amount})
    
    def calc_weight_amount(self, cr, uid, ids, context=None):
        if context is None: context = {}
        dpd_weight_prod_pool = self.pool.get('dpd.weight.product')
        for picking in self.browse(cr, uid, ids, context=context):
            if picking.country_id and picking.country_id.code =='DE':
                country = 'inside'
            else:
                country = 'outside'
            if picking.weight <= 0:
                weight_amount = 0.0
            else:
                weight = float(picking.weight)
                dpd_weight_product_ids = dpd_weight_prod_pool.search(cr, uid, 
                         [('min_weight','<=', weight),('max_weight','>=', weight),('country','=',country)])
                if dpd_weight_product_ids:
                    weight_amount = dpd_weight_prod_pool.browse(cr, uid, dpd_weight_product_ids[0], context).amount
                else:
                    raise osv.except_osv(('Warning!'),('Weight Product not found for weight %s!'%(weight)))
        return self.write(cr, uid, ids, {'weight_amount': weight_amount})

    def create(self, cr, uid, vals, context=None):
        if context is None: context = {}
        if vals and 'sending_with_us' in vals:
            company = self.pool.get('res.company').browse(cr, uid, vals['company_id'])
            sender = self.pool.get('res.partner').browse(cr, uid, vals['sender_id'])
            if vals['sending_with_us'] == True:
                sender_name = company.name + '/' + sender.name
            else:
                sender_name = sender.name
        else:
            sender_name = sender.name
            vals.update({'sender_name': sender_name})
        id_c = super(dpd_shipping, self).create(cr, uid, vals, context)
        self.write(cr, uid, [id_c], {'sending_with_us':vals.get('sending_with_us',False)})
        return id_c

    def write(self, cr, uid, ids, vals, context=None):
        if context is None: context = {}
        if vals.has_key('sending_with_us'):
            for this_obj in self.browse(cr, uid, ids, context):
                comp = vals.has_key('company_id') and vals['company_id'] or this_obj.company_id.id
                company = self.pool.get('res.company').browse(cr, uid, comp)
                send = vals.has_key('sender_id') and vals['sender_id'] or this_obj.sender_id.id
                sender = self.pool.get('res.partner').browse(cr, uid, send)
                if vals['sending_with_us'] == True:
                    sender_name = company.name + '/' + sender.name
                else:
                    sender_name = sender.name
                vals.update({'sender_name': sender_name})
        return super(dpd_shipping, self).write(cr, uid, ids, vals, context=context)

    def get_express_packing(self, cr, uid, ids, context=None):
        if context is None: context = {}
        for this_obj in self.browse(cr, uid, ids, context):
            dpd_weight_prod_pool = self.pool.get('dpd.weight.product')
            weight = float(this_obj.weight)
            if this_obj.country_id and this_obj.country_id.code =='DE':
                country = 'inside'
            else:
                country = 'outside'
            if weight <= 0.0:
                raise osv.except_osv(('Invaild Data!'),('Weight should not be Zero or Negative!'))
            dpd_weight_product_ids = dpd_weight_prod_pool.search(cr, uid, 
                         [('min_weight','<=', weight),('max_weight','>=', weight),('country','=',country)])
            if dpd_weight_product_ids:
                product_id = dpd_weight_prod_pool.browse(cr, uid, dpd_weight_product_ids[0], context).product_id.id
                self.create_do(cr, uid, this_obj, product_id, context)
                self.calc_weight_amount(cr, uid, [this_obj.id], context)
            else:
                raise osv.except_osv(('Warning!'),('Weight Product not found for weight %s!'%(weight)))
        return True

    def create_do(self, cr, uid, dpd_shipping_obj, product_id, context=None):
        if context is None: context = {}
        stock_picking_out_pool = self.pool.get('stock.picking.out')
        stock_move_pool = self.pool.get('stock.move')
        context.update({'picking_type': 'out','default_type': 'out'})
        do_default_fields = stock_move_pool.fields_get(cr, uid, context=context)
        do_default = stock_move_pool.default_get(cr, uid, do_default_fields, context=context)
        onchange_product = stock_move_pool.onchange_product_id(cr, uid, [], 
                   prod_id=product_id,partner_id=dpd_shipping_obj.partner_id.id)
        onchange_product = onchange_product.has_key('value') and onchange_product['value'] or {}
        do_default.update(onchange_product)
        do_default.update({'product_id': product_id,})
        do_data = {
            'partner_id': dpd_shipping_obj.partner_id.id,
            'delivery_type': 'dpd',
            'move_lines': [(0,0,do_default)]
        }

        do_id = stock_picking_out_pool.create(cr, uid, do_data, context)
        #write found weight product in dpd.shipping form
        self.write(cr, uid, [dpd_shipping_obj.id], {'weight_product_id': product_id}, context)
        stock_picking_out_pool.write(cr, uid, [do_id], {'dpd_shipping_id': dpd_shipping_obj.id})
        #CONFIRM DO
        stock_picking_out_pool.draft_force_assign(cr, uid, [do_id], context)
        #force AVAILBLE
        stock_picking_out_pool.force_assign(cr, uid, [do_id], context)
        return do_id

    def print_via_gcp(self, cr, uid, ids, context=None):
        if context is None: context = {}
        gcp_printer_wizard_pool = self.pool.get('gcp.printer.wizard')
        gcp_default_fields = gcp_printer_wizard_pool.fields_get(cr, uid, context=context)
        gcp_default = gcp_printer_wizard_pool.default_get(cr, uid, gcp_default_fields, context=context)
        if 'gcp_conf_id' not in gcp_default or not gcp_default['gcp_conf_id']:
            raise osv.except_osv(('Invaild Data!'),('Google Cloud Printing account not configured! Please configure account to Setting >> Google Cloud Printing >> Google Accounts.'))
        if 'printer_id' not in gcp_default or not gcp_default['printer_id']:
            raise osv.except_osv(('Invaild Data!'),('No default printer found! Please select default printer from Setting >> Google Cloud Printing >> Google Accounts.'))
        context.update({'active_model': 'dpd.shipping', 'active_ids': ids, 'active_id': ids[0]})
        wiz_id = gcp_printer_wizard_pool.create(cr, uid, 
                        {'printer_id': gcp_default.get('printer_id'),
                         'gcp_conf_id': gcp_default.get('gcp_conf_id'),
                         'model': 'dpd.shipping'})
        gcp_printer_wizard_pool.action_submit_job_dpd_shipping(cr, uid, [wiz_id], context=context)
        return True

dpd_shipping()

class dpd_weight_product(osv.osv):
    _name = "dpd.weight.product"
    _rec_name = "product_id"
    _columns = {
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'min_weight': fields.float('Min. Weight', required=True),
        'max_weight': fields.float('Max. Weight', required=True),
        'amount': fields.float('Price', required=True),
        'country':fields.selection([('inside','Germany'),('outside','Outside Germany')],string="Country")
    }
dpd_weight_product()

class create_shipping_invoice(osv.osv_memory):
    _inherit = 'create.shipping.invoice'

    _columns = {
        'product_id': fields.many2one('product.product', 'Product', required=True),
    }

    def create_invoice(self, cr, uid, ids, context=None):
        """ Creates customer invoice for DPD shipment
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        @return: A dictionary which loads customer invoice form view.
        """
        shipping_obj = self.pool.get('dpd.shipping')
        invoice_obj = self.pool.get('account.invoice')
        invoice_line_obj = self.pool.get('account.invoice.line')
        data_obj = self.pool.get('ir.model.data')
        dpd_ids = context.get('active_ids')
        for dpd_shipping in shipping_obj.browse(cr, uid, dpd_ids):
            if dpd_shipping.invoice_to == 'sender':
                partner_id = dpd_shipping.sender_id.id
            else:
                partner_id = dpd_shipping.partner_id.id
            inv_type = 'out_invoice'
            partner_onchange = invoice_obj.onchange_partner_id(cr, uid, [], inv_type, partner_id)
            partner_onchange = partner_onchange.has_key('value') and partner_onchange['value'] or {}
            invoice_vals = {
                'dpd_shipping_id': dpd_shipping.id,
                'type': inv_type,
                'partner_id': partner_id,
                'date_invoice': time.strftime('%Y-%m-%d'),
                'company_id': dpd_shipping.sender_id.company_id and dpd_shipping.sender_id.company_id.id or False,
                'user_id': uid,
            }
            partner_onchange.update(invoice_vals)
            invoice_id = invoice_obj.create(cr, uid, partner_onchange, context=context)

            product = self.browse(cr, uid, ids[0]).product_id
            uos_id = product.uos_id or product.uom_id or None
            tax_ids = product.taxes_id
            if tax_ids:
                tax_ids = map(lambda x: x.id, tax_ids)
            else:
                tax_ids=[]
            if product.property_account_income:
                line_account_id = product.property_account_income.id
            else:
                if product.categ_id.property_account_income_categ:
                    line_account_id = product.categ_id.property_account_income_categ.id
                else:
                    raise osv.except_osv(('Validation Error!'),("Invoice cannot validate because neither product nor product category property account income configured for product '%s'!"%(product.name)))
            tracking_no = dpd_shipping.tracking_number[3:]
            invoice_line_vals = {
                'name': 'Recipient: %s\nPackaging Number: %s\nWeight: %s'%(
                          dpd_shipping.partner_id.name,tracking_no,dpd_shipping.weight),
                'invoice_id': invoice_id,
                'uos_id': uos_id and uos_id.id or None,
                'product_id': product.id,
                'account_id': line_account_id,
                'price_unit': dpd_shipping.weight_amount,
#                 'discount': self._get_discount_invoice(cr, uid, move_line),
                'quantity': 1.00,
                'invoice_line_tax_id': [(6, 0, tax_ids)],
            #    'account_analytic_id': self._get_account_analytic_invoice(cr, uid, picking, move_line),            
            }
            invoice_line_id = invoice_line_obj.create(cr, uid, invoice_line_vals, context=context)
            invoice_obj.button_compute(cr, uid, [invoice_id], context=context,
                    set_total=(inv_type in ('in_invoice', 'in_refund')))
            
            shipping_obj.write(cr, uid, [dpd_shipping.id], {'state': 'invoiced'})
            
        id2 = data_obj._get_id(cr, uid, 'account', 'invoice_form')
        id3 = data_obj._get_id(cr, uid, 'account', 'invoice_tree')
        if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id
        if id3:
            id3 = data_obj.browse(cr, uid, id3, context=context).res_id

        return {
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'res_id' : invoice_id,
            'views': [(id2,'form'),(id3,'tree')],
            'type': 'ir.actions.act_window',
         }
create_shipping_invoice()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
