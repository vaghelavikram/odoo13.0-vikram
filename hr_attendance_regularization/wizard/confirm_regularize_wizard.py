# -*- coding: utf-8 -*-
from odoo import models, fields, api

class confirmWizard(models.TransientModel):
    _name = 'regularize.confirm.wizard'
    _description = 'Regularize Confirm Wizard'

    text = fields.Char(string="Text", default="Your Worked hours are exceed from office worked hours.")
