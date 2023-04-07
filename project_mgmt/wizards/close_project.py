# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CloseProject(models.TransientModel):
    _name = 'close.project'
    _description = 'Close Project'

    actual_start_date = fields.Date(string="Actual Start Date")
    actual_end_date = fields.Date(string="Actual End Date")

    def act_close_project(self):
        active_id = self._context.get('active_id')
        project = self.env['project.project'].search([('id', '=', active_id)])
        project.write({
            'actual_end_date': self.actual_end_date,
            'planned_end_date': self.actual_end_date,
        })
        project.action_closed()
