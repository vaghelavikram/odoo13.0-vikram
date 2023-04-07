# -*- coding: utf-8 -*-

from odoo import fields, models, api, _

class ResCompany(models.Model):
    _inherit = "res.company"

    company_signature = fields.Binary(string='Digital Signature', help="Field for adding the signature of the company")
    letterhead_watermark = fields.Binary(string='Watermark for Letter', help="Image size should be 679*600px for watemark in report")
