# -*- coding: utf-8 -*-

from odoo import fields, models


class AgreementType(models.Model):
    _name = "agreement.type"
    _description = "Agreement Types"

    name = fields.Char(string="Name", required=True)
    active = fields.Boolean(default=True)
