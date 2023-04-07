# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ContractType(models.Model):
    _name = 'hr.contract.type'


class EmployeeEntryDocuments(models.Model):
    _name = 'employee.checklist'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Employee Documents"

    def name_get(self):
        result = []
        for each in self:
            if each.document_type == 'entry':
                name = each.name
            elif each.document_type == 'exit':
                name = each.name
            elif each.document_type == 'other':
                name = each.name
            elif each.document_type == 'confirmation':
                name = each.name
            result.append((each.id, name))
        return result

    name = fields.Char(string='Name', copy=False, required=1)
    document_type = fields.Selection([('entry', 'Entry Process'),
                                      ('exit', 'Exit Process'),
                                      ('other', 'Optional'),
                                      ('confirmation', 'Confirmation Process')], string='Checklist Type', help='Type of Checklist', readonly=1, required=1)
    company_id = fields.Many2many('res.company', string="Company", groups="base.group_multi_company")
    emp_category_ids = fields.Many2many('hr.contract.type', string="e-Zestian Category")


class HrEmployeeDocumentInherit(models.Model):
    _inherit = 'hr.employee.document'

    @api.onchange('document_type')
    def _get_document_name(self):
        if self.document_type and self.document_type == 'entry':
            return {'domain': {'document_name': [('document_type', 'in', ['entry']), ('emp_category_ids', '=', self.employee_ref.employee_category.id), ('company_id', '=', self.employee_ref.company_id.id)]}}
        elif self.document_type and self.document_type == 'other':
            return {'domain': {'document_name': [('document_type', 'in', ['other']), ('emp_category_ids', '=', self.employee_ref.employee_category.id), ('company_id', '=', self.employee_ref.company_id.id)]}}
        else:
            return {'domain': {'document_name': [('document_type', 'in', ['exit'])]}}

    @api.onchange('document_name', 'document_type')
    def _get_checklist(self):
        emp_checklist = self.employee_ref.entry_checklist
        checklist = self.env['employee.checklist'].search([('document_type', '=', self.document_type), ('emp_category_ids', '=', self.employee_ref.employee_category.id), ('company_id', '=', self.employee_ref.company_id.id)])
        entry_list = [i.id for i in checklist if i not in emp_checklist]
        return {'domain': {'document_name': [('id', 'in', entry_list)]}}

    document_type = fields.Selection([('entry','Entry'), ('other', 'Optional'), ('exit','Exit')], string="Document Type", default="entry")
    document_name = fields.Many2one('employee.checklist', string='Document', help='Type of Document', required=True)
