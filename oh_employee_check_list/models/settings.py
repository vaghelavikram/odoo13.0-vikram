# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HRSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_checklist = fields.Boolean(string='Enable Checklist Progress in Kanban?', default=False)
    file_size = fields.Char(string='Upload File Size', default=5, config_parameter='oh_employee_check_list.file_size')

    @api.model
    def get_values(self):
        res = super(HRSettings, self).get_values()
        config = self.env['ir.config_parameter'].sudo()
        enable_checklist = config.get_param('employee_check_list.enable_checklist', default=False)
        res.update(
            enable_checklist=enable_checklist
        )
        return res

    def set_values(self):
        super(HRSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('employee_check_list.enable_checklist',
                                                         self.enable_checklist)
        emp_obj = self.env['hr.employee'].search([])
        for rec in emp_obj:
            rec.write({'check_list_enable': self.enable_checklist})

