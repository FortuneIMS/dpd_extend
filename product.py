
from openerp.osv import osv, fields

class product_template(osv.osv):
    _inherit = "product.template"
    
    def change_uom(self, cr, uid, query, context=None):
        cr.execute(query)
        res = cr.fetchall()
        return res