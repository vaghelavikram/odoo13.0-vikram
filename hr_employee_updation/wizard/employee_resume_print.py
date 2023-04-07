# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class EmployeeResumeWizard(models.TransientModel):
    _name = 'employee.resume.format'
    _description = 'Employee Resume Wizard'

    employee_id = fields.Many2one('hr.employee', string="e-Zestian")
    mobile_phone = fields.Boolean(string="Mobile Phone", default="True")
    work_email = fields.Boolean(string="Work Email", default="True")
    address = fields.Boolean(string="Address", default="True")
    birthday = fields.Boolean(string="Birthday", default="True")
    nationality = fields.Boolean(string="Nationality", default="True")

    def action_print_report(self):
        self.ensure_one()
        [data] = self.read()
        employees = self.env['hr.employee'].browse(self.employee_id.id)
        datas = {
            'form': data
        }
        return self.env.ref('hr_employee_updation.employee_resume_format').report_action(employees, data=datas)


class ReportEmployeeResume(models.AbstractModel):
    _name = 'report.hr_employee_updation.print_employee_resume_format'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form') or not self.env.context.get('active_model'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))
        return {
            'data': data['form'],
            'docs': docs,
        }
