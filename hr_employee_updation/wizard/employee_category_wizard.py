# -*- coding: utf-8 -*-

from odoo import fields, models


class EmployeeChangeCategoryWizard(models.TransientModel):
    _name = 'employee.change.category.wizard'
    _description = 'Employee Change category Wizard'

    employee_id = fields.Many2one('hr.employee', string="e-Zestian")
    employee_category = fields.Many2one('hr.contract.type', string="Team Member Category")
    generate_id = fields.Boolean(string="Generate New ID")
    exit_date = fields.Date(string="Exit Date")

    def action_change_category(self):
        if self.employee_id:
            self.employee_id.employee_category = self.employee_category.id
            if self.employee_category.name == 'Contractor':
                self.employee_id.exit_date = self.exit_date
            if self.employee_category.name == 'eZestian':
                self.employee_id.exit_date = False
            if self.generate_id:
                self.employee_id.identification_id = 'New'
