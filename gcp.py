# -*- coding: utf-8 -*-

from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.tools as tools
from openerp.addons.dpd import dpd_request
import datetime
import time
from openerp.addons.google_cloud_printing import gcp
import openerp.addons.decimal_precision as dp

class gcp_printer_wizard(osv.osv_memory):
    _inherit = 'gcp.printer.wizard'
    _columns = {
        'report_id': fields.many2one('ir.actions.report.xml', "Report"),
    }
    def action_submit_job_dpd_shipping(self, cr, uid, ids, context=None):
        if context is None: context = {}
        gcp_conf_pool = self.pool.get('gcp.conf')
        for obj in self.browse(cr, uid, ids, context):
            #prepare data as base64
#             ir_actions_report = self.pool.get('ir.actions.report.xml')
#             matching_reports = ir_actions_report.search(cr, uid, [('id','=',obj.report_id.id)])
#             if matching_reports:
#                 report = ir_actions_report.browse(cr, uid, matching_reports[0])
#                 report_service = 'report.' + report.report_name
#                 service = netsvc.LocalService(report_service)
#                 (jobsrc, format) = service.create(cr, uid, context.get('active_ids'), {'model': context.get('active_model')}, context=context)
            attachment_pool = self.pool.get("ir.attachment")
            print "obj.model...........",obj.model,context.get('active_ids',[])
            attachement_ids = attachment_pool.search(cr, uid, [('res_model','=',obj.model),
                                           ('res_id','in',context.get('active_ids',[]))])
            if attachement_ids:
                import base64
                datas = attachment_pool.browse(cr, uid, attachement_ids[0], context).datas
                jobsrc = base64.decodestring(datas)
            else:
                raise osv.except_osv(_('Error!'), _('Attachment Document not found!'))
            result = gcp.SubmitJob(obj.printer_id.printer_id, 'pdf', jobsrc, obj.gcp_conf_id.google_email, obj.gcp_conf_id.google_password, 'Print Label')
#             print "RESULT: ================> ",result
        self_obj = self.browse(cr, uid, ids[0], context)
        return True
gcp_printer_wizard()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
