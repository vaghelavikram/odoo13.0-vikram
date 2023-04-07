# -*- coding: utf-8 -*-

from odoo import fields, models


TIMELINE_VIEW = ('timeline', 'Timeline')


class IrUIView(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=[TIMELINE_VIEW])
