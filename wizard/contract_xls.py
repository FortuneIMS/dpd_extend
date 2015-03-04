# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2012-2013 2Vive. All Rights Reserved.
#    Author: Sanket M0odi <sanket.msc9@gmail.com>
#
##############################################################################

from openerp.osv import fields, osv
# from openpyxl import workbook
# from openpyxl.style import Border,Color,Fill
from openerp.tools.translate import _
from openerp import tools
import base64
import os
import copy
from datetime import datetime,timedelta,date
import time, dateutil, dateutil.tz
from dateutil.relativedelta import relativedelta
from tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from compiler.ast import flatten
import tempfile
import xlsxwriter

FLOAT_FORMAT = '_(* #,##0.00_);_(* (#,##0.00);_(* "-"??_);_(@_)'

class contract_xls_report(osv.osv_memory):
    _name = "contract.xls.report"
    _description = "contract detailed report, Export as xlsx format wizard"
    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required=True),

        'data': fields.binary('File', readonly=True),
        'name': fields.char('Filename', 128, readonly=True),
        'advice': fields.text('Advice', readonly=True),
        'state': fields.selection([('choose','choose'), ('get','get')],'State'),
    }

    def _get_company_id(self,cr,uid, context=None):
        if context is None:
            context={}
        company_id = self.pool.get('res.users').read(cr,uid,uid,['company_id'])['company_id']
        return company_id and company_id[0] or False

    _defaults = {
        'state': lambda *a: 'choose',
        'name': lambda *a: 'lang.tar.gz',
        'company_id': _get_company_id,
    }

    def print_xlsxwriter_report(self, cr, uid, ids, context=None):
        if context is None: context = {}
        this = self.browse(cr, uid, ids)[0]
        filename = 'Contract-Report(%s).xlsx' % (this.company_id.name)
        this.name = filename.replace(':','-')
        title = 'Contract-Detailed-Report(%s)' % (this.company_id.name)

        # Create a workbook and add a worksheet.
        workbook = xlsxwriter.Workbook('/tmp/' + filename)
        worksheet = workbook.add_worksheet()

        ######## FOTMATING #########
        # STANDAR LEFT ALIGNMENT.
        data_left = workbook.add_format({'font_size': 10,
                                         'align': 'left',
                                         'valign': 'vcenter'
                                           })
        # STANDAR RIGHT ALIGNMENT.
        data_right = workbook.add_format({'font_size': 10,
                                         'align': 'right',
                                         'valign': 'vcenter'
                                           })
        # STANDAR center ALIGNMENT.
        data_center = workbook.add_format({'font_size': 10,
                                         'align': 'center',
                                         'valign': 'vcenter'
                                           })
        # Set up some formats to use.
        red = workbook.add_format({'color': 'red'})
        #HEADER FORMAT
        header_format = workbook.add_format({'align': 'center',
                                           'valign': 'vcenter',
                                           'bold': 1,
                                           'fg_color': '#B2B2B2',
                                           'border': 1,})
        # TITLE / MERGE CELL FORMATE.
        title_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'fg_color': 'yellow',
            'font_size': 16})
        # SET ROW HEIGHT
        worksheet.set_row(1, 24)
        # SET COLUMN SIZE(WIDTH)
        worksheet.set_column('A:L', 15)
        ########### FORMATING END ##################

        # Merge 3 cells
        worksheet.merge_range('A2:L2', title, title_format)
        row = 1
        row += 2

        columns = ['Order Reference','First Name','Last Name','Is a Company?',
                   'Box/Code','Move In','Contract Date','Actual Price',
                   'Discount Price','Discount%','Regular Box Price','Surface M2']
        col = 0
        for header in columns:
            worksheet.write(row, col, header, header_format)
            col += 1

        row += 1

        summary_query = """
SELECT 
    so.name,
    p.first_name,
    p.last_name,
    p.is_company,
    prod.default_code,
    so.move_in,
    so.date,
    sol.actual_price,
    sol.discount_price,
    sol.price_unit,
    prod.surface_m2
FROM
    sale_order_line as sol
INNER JOIN sale_order as so on so.id=sol.order_id
INNER JOIN res_partner as p on p.id=so.partner_id
INNER JOIN product_product as prod on prod.id=sol.product_id
INNER JOIN product_template as pt on pt.id=prod.product_tmpl_id
WHERE 
    so.contract_order=True AND
    prod.rent_categ=True AND 
    prod.is_cubix=False AND
    so.company_id=%s
GROUP BY
    prod.default_code,
    prod.surface_m2,
    so.move_in,
    so.date,
    so.name,
    p.first_name,
    p.last_name,
    p.is_company,
    sol.actual_price,
    sol.discount_price,
    sol.price_unit
ORDER BY
    so.move_in,
    so.date,
    so.name
        """%(this.company_id.id)

        cr.execute(summary_query)
        result = cr.fetchall()


        if not result:
            raise osv.except_osv(_('Warning'),_('No data to display for Fiscal Year %s of Company %s!'%(this.fiscalyear_id.code,this.company_id.name)))

#         print "result.................",result

        start = row + 1
        for element in result:
#             print "elemt..............",element
            col = 0
            order_reference = element[0]
            worksheet.write(row, col, order_reference, data_left)

            col += 1
            first_name = element[1]
            worksheet.write(row, col, first_name, data_left)

            col += 1
            last_name = element[2]
            worksheet.write(row, col, last_name, data_left)

            col += 1
            if not element[3]:
                company = 0
            else:
                company = 1
            worksheet.write(row, col, company, data_center)

            col += 1
            box_code = element[4]
            worksheet.write(row, col, box_code, data_left)

            col += 1
            move_in = element[5]
            worksheet.write(row, col, move_in, data_center)

            col += 1
            contract_date = element[6]
            worksheet.write(row, col, contract_date, data_center)

            col += 1
            actual_price = element[7]
            worksheet.write(row, col, actual_price, data_right)

            col += 1
            discount_price = element[8]
            worksheet.write(row, col, discount_price, data_right)

            col += 1
            discount_per = ''
            worksheet.write(row, col, discount_per, data_right)
#             ws.cell(row = row, column = col).value = element[9]

            col += 1
            regular_box_price = element[9]
            worksheet.write(row, col, regular_box_price, data_right)

            col += 1
            surface_m2 = element[10]
            worksheet.write(row, col, surface_m2, data_right)
            row += 1

        end = row
        ########### FIRST TABLE START ########
        row += 2
        col=1
        worksheet.write(row, col, 'Amount of Tenant', data_left)
        col=2
        worksheet.write_formula(row, col, '=COUNTA(B%d:B%d)'%(start,end), data_right)

        row += 1
        col=1
        worksheet.write(row, col, 'Total Rented Area', data_left)
        col=2
        worksheet.write_formula(row, col, '=SUM(L%d:L%d)'%(start,end), data_right)

        row += 1
        col=1
        worksheet.write(row, col, 'Total Area', data_left)
        col=2
        worksheet.write(row, col, '4100.00', data_right)

        row += 1
        col=1
        worksheet.write(row, col, 'Vacant Area', data_left)
        col=2
        worksheet.write_formula(row, col, '=ROUND(C%s-C%s,5)'%(row-1,row), data_right)
        ########### FIRST TABLE END ########



        ########### SECOND TABLE START ########
        row += 2
        col=1
        worksheet.write(row, col, 'Total Rented Per period', data_left)
        col=2
        worksheet.write(row, col, '=SUM(H%s:H%s)'%(start,end), data_right)

        row += 1
        col=1
        worksheet.write(row, col, 'Total Rent Per Month', data_left)
        col=2
        worksheet.write_formula(row, col, '=ROUND(C%s*13/12,5)'%(row), data_right)

        row += 1
        col=1
        worksheet.write(row, col, 'Average m2 Price', data_left)
        col=2
        worksheet.write_formula(row, col, '=ROUND(C%s/C%s,5)'%(row,row-5), data_right)

        row += 1
        col=1
        worksheet.write(row, col, 'Total Possible Rent', data_left)
        col=2
        worksheet.write_formula(row, col, '=ROUND(C%s*C%s,5)'%(row-5,row), data_right)
        ########### SECOND TABLE END ########



        ########### COMPANY AND PRIVATE START ########
        row += 2
        col=2
        worksheet.write(row, col, 'Count', data_left)
        col=3
        worksheet.write(row, col, 'Percentage', data_left)

        row += 1
        col=1
        worksheet.write(row, col, 'Amount of Company', data_left)
        col=2
        worksheet.write_formula(row, col, '=COUNTIF(D%s:D%s,">0")'%(start,end), data_right)
        col=3
        worksheet.write_formula(row, col, '=ROUND((100*C%s)/C%s,5)'%(row+1,row+3), data_right)

        row += 1
        col=1
        worksheet.write(row, col, 'Amount of Privat', data_left)
        col=2
        worksheet.write_formula(row, col, '=COUNTIF(D%s:D%s,"=0")'%(start,end), data_right)
        col=3
        worksheet.write_formula(row, col, '=ROUND((100*C%s)/C%s,5)'%(row+1,row+2), data_right)

        row += 1
        col=1
        worksheet.write(row, col, 'Total', data_left)
        col=2
        worksheet.write_formula(row, col, '=SUM(C%s:C%s)'%(row-1,row), data_right)
        col=3
        worksheet.write_formula(row, col, '=SUM(D%s:D%s)'%(row-1,row), data_right)
        ########### COMPANY AND PRIVATE END ########


        workbook.close()
        ##########
        file_name = '/tmp/' + filename
        if tools.config.get('report_path', False):
            file_name = os.path.join(tools.config['report_path'], this.name)
#         workbook.save(file_name)

        this.advice = _("Save this document to a .XLSX file and open it with your favourite spreadsheet software.")
        tf = open(file_name, 'rb')
        buf = tf.read()
        out=base64.encodestring(buf)
        tf.close()
        os.remove(file_name)
        return self.write(cr, uid, ids, {'state':'get', 'data':out, 'advice':this.advice, 'name':this.name}, context=context)

    def print_xlsx_report(self, cr, uid, ids, context=None):
        if context is None: context = {}
        this = self.browse(cr, uid, ids)[0]
        filename = 'Contract-Report(%s).xlsx' % (this.company_id.name)
        this.name = filename.replace(':','-')

        wb = workbook.Workbook()#optimized_write = True

        #get it by using the openpyxl.workbook.Workbook.get_active_sheet() method
        ws = wb.get_active_sheet()

        #create new worksheets by using the openpyxl.workbook.Workbook.create_sheet() method
        title = 'Contract-Detailed-Report(%s)' % (this.company_id.name)
        #if this.account_report_id.name[:1] == 'C':
        #    title = 'Statement of Cash Flows'
        ws.title = title[:30]

        #To access a cell, use the openpyxl.worksheet.Worksheet.cell() method
        #c = ws.cell('A4') d = ws.cell(row = 4, column = 2)
        _cell = ws.cell('A1')
        _cell = ws.cell('B1')
        _cell = ws.cell('C1')
        _cell = ws.cell('D1')
        _cell = ws.cell('E1')
        _cell = ws.cell('F1')
        _cell = ws.cell('G1')
        _cell = ws.cell('H1')
        _cell = ws.cell('I1')
        _cell = ws.cell('J1')
        _cell = ws.cell('K1')
        _cell = ws.cell('L1')

        # Font properties
        ws.column_dimensions["A"].width = 20.0
        ws.column_dimensions["B"].width = 20.0
        ws.column_dimensions["C"].width = 20.0
        ws.column_dimensions["D"].width = 15.0
        ws.column_dimensions["E"].width = 15.0
        ws.column_dimensions["F"].width = 15.0
        ws.column_dimensions["G"].width = 15.0
        ws.column_dimensions["H"].width = 15.0
        ws.column_dimensions["I"].width = 15.0
        ws.column_dimensions["J"].width = 15.0
        ws.column_dimensions["K"].width = 15.0
        ws.column_dimensions["L"].width = 15.0

        ws.merge_cells('A%s:L%s'%(2,2))
        row = 1
        ws.row_dimensions[ws.cell(row = row, column = 0).row].height = 24
        ws.cell(row = row, column = 0).style.font.size = 16
        ws.cell(row = row, column = 0).style.font.bold = True
        ws.cell(row = row, column = 0).style.font.color.index = Color.DARKRED
        ws.cell(row = row, column = 0).style.alignment.horizontal = 'center'
        ws.cell(row = row, column = 0).style.borders.bottom.border_style = Border.BORDER_MEDIUM
        ws.cell(row = row, column = 0).style.borders.top.border_style = Border.BORDER_MEDIUM
        ws.cell(row = row, column = 0).style.borders.left.border_style = Border.BORDER_MEDIUM
        ws.cell(row = row, column = 0).style.borders.right.border_style = Border.BORDER_MEDIUM
        ws.cell(row = row, column = 0).value = title

        row += 2

        columns = ['Order Reference','First Name','Last Name','Is a Company?',
                   'Box/Code','Move In','Contract Date','Actual Price',
                   'Discount Price','Discount%','Regular Box Price','Surface M2']
        col = 0
        for header in columns:
            ws.cell(row = row, column = col).style.font.size = 10
            ws.cell(row = row, column = col).style.alignment.horizontal = 'center'
            ws.cell(row = row, column = col).style.fill.fill_type = Fill.FILL_SOLID
            ws.cell(row = row, column = col).style.fill.start_color.index = Color.GREEN
            ws.cell(row = row, column = col).style.font.bold = True
            ws.cell(row = row, column = col).style.borders.bottom.border_style = Border.BORDER_THIN
            ws.cell(row = row, column = col).style.borders.top.border_style = Border.BORDER_THIN
            ws.cell(row = row, column = col).style.borders.left.border_style = Border.BORDER_THIN
            ws.cell(row = row, column = col).style.borders.right.border_style = Border.BORDER_THIN
            ws.cell(row = row, column = col).value = header
            col += 1

        row += 1

        summary_query = """
SELECT 
    so.name,
    p.first_name,
    p.last_name,
    p.is_company,
    prod.default_code,
    so.move_in,
    so.date,
    sol.actual_price,
    sol.discount_price,
    sol.price_unit,
    prod.surface_m2
FROM
    sale_order_line as sol
INNER JOIN sale_order as so on so.id=sol.order_id
INNER JOIN res_partner as p on p.id=so.partner_id
INNER JOIN product_product as prod on prod.id=sol.product_id
INNER JOIN product_template as pt on pt.id=prod.product_tmpl_id
WHERE 
    so.contract_order=True AND
    prod.rent_categ=True AND 
    prod.is_cubix=False AND
    so.company_id=%s
GROUP BY
    prod.default_code,
    prod.surface_m2,
    so.move_in,
    so.date,
    so.name,
    p.first_name,
    p.last_name,
    p.is_company,
    sol.actual_price,
    sol.discount_price,
    sol.price_unit
ORDER BY
    so.move_in,
    so.date,
    so.name
        """%(this.company_id.id)

        cr.execute(summary_query)
        result = cr.fetchall()


        if not result:
            raise osv.except_osv(_('Warning'),_('No data to display for Fiscal Year %s of Company %s!'%(this.fiscalyear_id.code,this.company_id.name)))

#         print "result.................",result

        start = row + 1
        for element in result:
#             print "elemt..............",element
            col = 0
            ws.cell(row = row, column = col).style.font.size = 10
            ws.cell(row = row, column = col).style.alignment.horizontal = 'left'
            ws.cell(row = row, column = col).value = element[0]

            col += 1
            ws.cell(row = row, column = col).style.font.size = 10
            ws.cell(row = row, column = col).style.alignment.horizontal = 'left'
            ws.cell(row = row, column = col).value = element[1]

            col += 1
            ws.cell(row = row, column = col).style.font.size = 10
            ws.cell(row = row, column = col).style.alignment.horizontal = 'left'
            ws.cell(row = row, column = col).value = element[2]

            col += 1
            if not element[3]:
                company = 0
            else:
                company = 1
            ws.cell(row = row, column = col).style.font.size = 10
            ws.cell(row = row, column = col).style.alignment.horizontal = 'center'
            ws.cell(row = row, column = col).value = company

            col += 1
            ws.cell(row = row, column = col).style.font.size = 10
            ws.cell(row = row, column = col).style.alignment.horizontal = 'left'
            ws.cell(row = row, column = col).value = element[4]

            col += 1
            ws.cell(row = row, column = col).style.font.size = 10
            ws.cell(row = row, column = col).style.alignment.horizontal = 'center'
            ws.cell(row = row, column = col).value = element[5]

            col += 1
            ws.cell(row = row, column = col).style.font.size = 10
            ws.cell(row = row, column = col).style.alignment.horizontal = 'center'
            ws.cell(row = row, column = col).value = element[6]

            col += 1
            ws.cell(row = row, column = col).style.font.size = 10
            ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
            ws.cell(row = row, column = col).value = element[7]

            col += 1
            ws.cell(row = row, column = col).style.font.size = 10
            ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
            ws.cell(row = row, column = col).style.number_format.format_code = FLOAT_FORMAT
            ws.cell(row = row, column = col).value = element[8]

            col += 1
            ws.cell(row = row, column = col).style.font.size = 10
            ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
            ws.cell(row = row, column = col).style.number_format.format_code = FLOAT_FORMAT
#             ws.cell(row = row, column = col).value = element[9]

            col += 1
            ws.cell(row = row, column = col).style.font.size = 10
            ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
            ws.cell(row = row, column = col).style.number_format.format_code = FLOAT_FORMAT
            ws.cell(row = row, column = col).value = element[9]

            col += 1
            ws.cell(row = row, column = col).style.font.size = 10
            ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
            ws.cell(row = row, column = col).style.number_format.format_code = FLOAT_FORMAT
            ws.cell(row = row, column = col).value = element[10]
            row += 1

        end = row
        ########### FIRST TABLE START ########
        row += 2
        col=1
        ws.cell(row = row, column = col).style.font.size = 10
        ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
        ws.cell(row = row, column = col).value = "Amount of Tenant"
        col=2
        ws.cell(row = row, column = col).style.font.size = 10
        ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
        ws.cell(row = row, column = col).value = "=COUNTA(B%s:B%s)"%(start,end)

        row += 1
        col=1
        ws.cell(row = row, column = col).style.font.size = 10
        ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
        ws.cell(row = row, column = col).value = "Total Rented Area"
        col=2
        ws.cell(row = row, column = col).style.font.size = 10
        ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
        ws.cell(row = row, column = col).value = "=SUM(L%s:L%s)"%(start,end)

        row += 1
        col=1
        ws.cell(row = row, column = col).style.font.size = 10
        ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
        ws.cell(row = row, column = col).value = "Total Area"
        col=2
        ws.cell(row = row, column = col).style.font.size = 10
        ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
        ws.cell(row = row, column = col).value = "4100.00"

        row += 1
        col=1
        ws.cell(row = row, column = col).style.font.size = 10
        ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
        ws.cell(row = row, column = col).value = "Vacant Area"
        col=2
        ws.cell(row = row, column = col).style.font.size = 10
        ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
        ws.cell(row = row, column = col).value = "=ROUND(C%s-C%s,5)"%(row-1,row)
        ########### FIRST TABLE END ########



        ########### SECOND TABLE START ########
        row += 2
        col=1
        ws.cell(row = row, column = col).style.font.size = 10
        ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
        ws.cell(row = row, column = col).value = "Total Rented Per period"
        col=2
        ws.cell(row = row, column = col).style.font.size = 10
        ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
        ws.cell(row = row, column = col).value = "=SUM(H%s:H%s)"%(start,end)

        row += 1
        col=1
        ws.cell(row = row, column = col).style.font.size = 10
        ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
        ws.cell(row = row, column = col).value = "Total Rent Per Month"
        col=2
        ws.cell(row = row, column = col).style.font.size = 10
        ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
        ws.cell(row = row, column = col).value = "=ROUND(C%s*13/12,5)"%(row)

        row += 1
        col=1
        ws.cell(row = row, column = col).style.font.size = 10
        ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
        ws.cell(row = row, column = col).value = "Average m2 Price"
        col=2
        ws.cell(row = row, column = col).style.font.size = 10
        ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
        ws.cell(row = row, column = col).value = "=ROUND(C%s/C%s,5)"%(row,row-5)

        row += 1
        col=1
        ws.cell(row = row, column = col).style.font.size = 10
        ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
        ws.cell(row = row, column = col).value = "Total Possible Rent"
        col=2
        ws.cell(row = row, column = col).style.font.size = 10
        ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
        ws.cell(row = row, column = col).value = "=ROUND(C%s*C%s,5)"%(row-5,row)
        ########### SECOND TABLE END ########



        ########### COMPANY AND PRIVATE START ########
        row += 2
        col=2
        ws.cell(row = row, column = col).style.font.size = 10
        ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
        ws.cell(row = row, column = col).value = "Count"
        col=3
        ws.cell(row = row, column = col).style.font.size = 10
        ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
        ws.cell(row = row, column = col).value = "Percentage%"

        row += 1
        col=1
        ws.cell(row = row, column = col).style.font.size = 10
        ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
        ws.cell(row = row, column = col).value = "Amount of Company"
        col=2
        ws.cell(row = row, column = col).style.font.size = 10
        ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
        ws.cell(row = row, column = col).value = '=COUNTIF(D%s:D%s,">0")'%(start,end)
        col=3
        ws.cell(row = row, column = col).style.font.size = 10
        ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
        ws.cell(row = row, column = col).value = "=ROUND((100*C%s)/C%s,5)"%(row+1,row+3)

        row += 1
        col=1
        ws.cell(row = row, column = col).style.font.size = 10
        ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
        ws.cell(row = row, column = col).value = "Amount of Privat"
        col=2
        ws.cell(row = row, column = col).style.font.size = 10
        ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
        ws.cell(row = row, column = col).value = '=COUNTIF(D%s:D%s,"=0")'%(start,end)
        col=3
        ws.cell(row = row, column = col).style.font.size = 10
        ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
        ws.cell(row = row, column = col).value = "=ROUND((100*C%s)/C%s,5)"%(row+1,row+2)

        row += 1
        col=1
        ws.cell(row = row, column = col).style.font.size = 10
        ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
        ws.cell(row = row, column = col).value = "Total"
        col=2
        ws.cell(row = row, column = col).style.font.size = 10
        ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
        ws.cell(row = row, column = col).value = "=SUM(C%s:C%s)"%(row-1,row)
        col=3
        ws.cell(row = row, column = col).style.font.size = 10
        ws.cell(row = row, column = col).style.alignment.horizontal = 'right'
        ws.cell(row = row, column = col).value = "=SUM(D%s:D%s)"%(row-1,row)
        ########### COMPANY AND PRIVATE END ########

        file_name = '/tmp/' + this.name
        if tools.config.get('report_path', False):
            file_name = os.path.join(tools.config['report_path'], this.name)
        wb.save(file_name)

        ##########
        this.advice = _("Save this document to a .XLSX file and open it with your favourite spreadsheet software.")
        tf = open(file_name, 'rb')
        buf = tf.read()
        out=base64.encodestring(buf)
        tf.close()
        os.remove(file_name)
        return self.write(cr, uid, ids, {'state':'get', 'data':out, 'advice':this.advice, 'name':this.name}, context=context)

    def print_reset(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'choose', 'data': False, 
                                         'advice': False, 'name': False,
                                         }, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
