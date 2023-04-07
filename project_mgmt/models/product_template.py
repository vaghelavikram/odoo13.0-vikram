# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError


class ProductTemplateInherit(models.Model):
    _inherit = 'product.template'

    @api.onchange('job_id')
    def _onchange_job_id(self):
        for rec in self:
            rec.sudo().write({
                'name': rec.job_id.name
            })

    @api.onchange('service_policy')
    def _onchange_service_policy(self):
        for rec in self:
            if rec.service_policy == 'delivered_timesheet':
                rec.sudo().write({
                    'is_tnm': True
                })
            if rec.service_policy == 'delivered_manual':
                rec.sudo().write({
                    'is_tnm': False
                })

    def _get_default_uom_id(self):
        return self.env["uom.uom"].search([('name', '=', 'Hours')], limit=1, order='id').id

    job_id = fields.Many2one("hr.job", string="Designation")
    is_tnm = fields.Boolean(string="Tnm")
    uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure',
        default=_get_default_uom_id, required=True,
        help="Default unit of measure used for all stock operations.")
    uom_po_id = fields.Many2one(
        'uom.uom', 'Purchase Unit of Measure',
        default=_get_default_uom_id, required=True,
        help="Default unit of measure used for purchase orders. It must be in the same category as the default unit of measure.")
    show_all_role = fields.Boolean('Show All Product')