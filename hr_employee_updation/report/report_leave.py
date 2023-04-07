# -*- coding: utf-8 -*-
from odoo import models, api, fields, _


class LeaveAllocationSummaryXlsx(models.AbstractModel):
    _name = 'report.hr_employee_updation.report_leave_allocation_summary'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Report Rport Leave Allocation Summary'

    def generate_xlsx_report(self, workbook, data, lines):
        sheet = workbook.add_worksheet("Print Leave Summary %s"%(fields.Date.today().strftime('%d-%b-%Y')))
        bold = workbook.add_format({'bold': True})
        sheet.write(0, 0, 'e-Zestian Name', bold)
        sheet.write(0, 1, 'e-Zestian ID', bold)
        sheet.write(0, 2, 'Privilege Leave', bold)
        sheet.write(0, 3, 'Casual Leave', bold)
        sheet.write(0, 4, 'Optional Leave', bold)
        sheet.write(0, 5, 'Total Leaves', bold)
        count = 1
        for rec in lines:
            # leave = self.env['hr.leave.report'].search([('employee_id','=',rec.id)])
            leave = self.env['hr.leave.report'].search([('employee_id', '=', 838)])
            pl = leave.filtered(lambda r: r.holiday_status_id.name == 'Privilege Leave')
            total_pl = sum([rec.number_of_days for rec in pl]) if pl else ''
            cl = leave.filtered(lambda r: r.holiday_status_id.name == 'Casual Leave')
            total_cl = sum([rec.number_of_days for rec in cl]) if cl else '' 
            ol = leave.filtered(lambda r: r.holiday_status_id.name == 'Optional Holidays')
            total_ol = sum([rec.number_of_days for rec in ol]) if ol else ''
            sheet.write(count, 0, rec.name, False)
            sheet.write(count, 1, rec.identification_id, False)
            sheet.write(count, 2, total_pl, False)
            sheet.write(count, 3, total_cl, False)
            sheet.write(count, 4, total_ol, False)
            sheet.write(count, 5, rec.leaves_count, False)
            count += 1
