# -*- coding: utf-8 -*-
{
    'name': 'Mybox Erp Extend',
    'category': 'Customized',
    'version': '1.0',
    'description': 'Mybox ERP module extends',
    'depends': ["base","dpd","google_cloud_printing"],
    "init_xml": [],
    "update_xml": [ 
                   "dpd_view.xml",
                   "gcp_view.xml",
                   "wizard/contract_xls_view.xml",
                   "security/ir.model.access.csv",
                   ],
    'js':[ ],
    'css':[ ],
    'qweb': [ ],
    'demo_xml': [ ],
    'test':[ ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 0,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
