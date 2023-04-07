# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ExtendProjectInherit(models.TransientModel):
    _inherit = 'extend.project'

    def _get_project_allocations(self):
        if self.env.context.get('active_model') == 'sale.order':
            order = self.env['sale.order'].browse(self.env.context.get('active_id'))
            active_id = order.project_id.id
        else:
            active_id = self.env.context.get('active_id')
        project = self.env['project.project'].browse(active_id)
        if project:
            assignment = [k.id for k in project.assignment_ids if k.assign_status == 'confirmed' and k.end_date == project.planned_end_date]
            return assignment

    allocation_ids = fields.Many2many('project.assignment', string="Allocations", default=_get_project_allocations)
