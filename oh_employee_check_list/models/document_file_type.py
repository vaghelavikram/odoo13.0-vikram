# -*- coding: utf-8 -*-

from odoo import models, fields, api


class DocumentsFileType(models.Model):
    _name = 'document.file.type'
    _description = "Document File Type"

    name = fields.Char(string='Upload File Type', help="Following file types are allowed while Uploading any document.")
