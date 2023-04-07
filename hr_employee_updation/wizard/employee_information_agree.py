# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import base64
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class EmployeeInformationAgreeWizard(models.TransientModel):
    _name = 'employee.information.agree'
    _description = 'Employee Information Agree Wizard'

    employee_id = fields.Many2one('hr.employee', string="e-Zestian")

    def action_submit_information(self):
        if self.employee_id.id == self.env.user.employee_id.id:
            checklist = self.env['employee.checklist'].search([('name', '=', 'Information Agreement')])
            employee = self.env.user.employee_id
            employee.sudo().write({
                'entry_checklist': [(4, checklist.id)],
                'is_submit': True
                # 'nda_signed_off': fields.Date.today()
            })
            REPORT_ID = 'hr_employee_updation.employee_information_agreement'
            pdf = self.env.ref(REPORT_ID).render_qweb_pdf(employee.id)
            # pdf result is a list
            b64_pdf = base64.b64encode(pdf[0])
            # save pdf as attachment
            # ATTACHMENT_NAME = employee.name.lower() + '_information_agreement'
            # attach_id = self.env['ir.attachment'].sudo().create({
            #     'description': ATTACHMENT_NAME,
            #     'type': 'binary',
            #     'datas': b64_pdf,
            #     'name': ATTACHMENT_NAME + '.pdf',
            #     'store_fname': ATTACHMENT_NAME,
            #     'res_model': self._name,
            #     'res_id': employee.id,
            #     'mimetype': 'application/x-pdf'
            # })
            return self.env['hr.employee.document'].sudo().create({
                'document_type': 'entry',
                'document_name': checklist.id,
                'attach1': b64_pdf,
                'employee_ref': employee.id
            })
