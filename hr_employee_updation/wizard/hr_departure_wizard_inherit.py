# -*- coding: utf-8 -*-

from odoo import api, fields, models


class HrDepartureWizardInherit(models.TransientModel):
    _inherit = 'hr.departure.wizard'
    _description = 'Departure Wizard'


    departure_reason = fields.Selection([
        ('fired', 'Fired'),
        ('resigned', 'Resigned'),
        ('retired', 'Retired')
    ], string="Departure Reason", default="resigned")
