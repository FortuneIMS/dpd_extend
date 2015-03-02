# -*- coding: utf-8 -*-

from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.tools as tools
from openerp.addons.dpd import dpd_request
import datetime
import time
import openerp.addons.decimal_precision as dp

class account_invoice(osv.osv):
    _inherit = 'account.invoice'
    _columns = {
        'dpd_shipping_id': fields.many2one('dpd.shipping', "DPD Shipping"),
    }
account_invoice()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
