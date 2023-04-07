# -*- coding: utf-8 -*-

from datetime import datetime, date, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import Warning


class HrEmployeeDocument(models.Model):
    _name = 'hr.employee.document'
    _description = 'HR Employee Documents'

    def mail_reminder(self):
        """Sending document expiry notification to employees."""

        now = datetime.now() + timedelta(days=1)
        date_now = now.date()
        match = self.search([])
        for i in match:
            if i.expiry_date:
                exp_date = fields.Date.from_string(i.expiry_date) - timedelta(days=7)
                if date_now >= exp_date:
                    mail_content = "  Hello  " + i.employee_ref.name + ",<br>Your Document " + i.name + "is going to expire on " + \
                                   str(i.expiry_date) + ". Please renew it before expiry date"
                    main_content = {
                        'subject': _('Document-%s Expired On %s') % (i.name, i.expiry_date),
                        'author_id': self.env.user.partner_id.id,
                        'body_html': mail_content,
                        'email_to': i.employee_ref.work_email,
                    }
                    self.env['mail.mail'].create(main_content).send()

    def download_content(self):
        self.ensure_one()
        if self.attach1:
            action = {
                'type': "ir.actions.act_url",
                'target': "current",
            }
            action['url'] = '/documents/content/%s' % self.id
            return action

        # if self.doc_attachment_id and self.doc_attachment_id.ids:
        #     action = {
        #         'type': "ir.actions.act_url",
        #         'target': "current",
        #     }
        #     action['url'] = '/documents/content/%s' % self.id
        #     return action

    @api.constrains('expiry_date')
    def check_expr_date(self):
        for each in self:
            if each.expiry_date:
                exp_date = fields.Date.from_string(each.expiry_date)
                if exp_date < date.today():
                    raise Warning('Your Document Is Expired.')

    def name_get(self):
        result = []
        for record in self:
            name = record.document_name.name
            result.append((record.id, name))
        return result

    name = fields.Char(string='Document Number', copy=False, help='You can give your'
                                                                                 'Document number.')
    description = fields.Text(string='Description', copy=False)
    expiry_date = fields.Date(string='Expiry Date', copy=False)
    employee_ref = fields.Many2one('hr.employee', copy=False)
    doc_attachment_id = fields.Many2many('ir.attachment', 'doc_attach_rel', 'doc_id', 'attach_id3', string="Attachments",
                                         help='You can attach the copy of your document', copy=False)
    attach1 = fields.Binary(string="Attachment", help='You can attach the copy of your document', copy=False)
    attach2 = fields.Binary(string="Second Attachment", help='You can attach the copy of your document', copy=False)
    issue_date = fields.Char(string='Issue Date1', copy=False)
    issue_date1 = fields.Date(string='Issue Date', copy=False)
    active = fields.Boolean(default=True)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def _document_count(self):
        for each in self:
            document_ids = self.env['hr.employee.document'].sudo().search([('employee_ref', '=', each.id)])
            each.document_count = len(document_ids)

    def document_view(self):
        self.ensure_one()
        domain = [
            ('employee_ref', '=', self.id)]
        return {
            'name': _('Documents'),
            'domain': domain,
            'res_model': 'hr.employee.document',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'help': _('''<p class="oe_view_nocontent_create">
                           Click to Create for New Documents
                        </p>'''),
            'limit': 80,
            'context': {'default_employee_ref': self.id} 
        }

    document_count = fields.Integer(compute='_document_count', string='# Documents')


class HrEmployeeAttachment(models.Model):
    _inherit = 'ir.attachment'

    doc_attach_rel = fields.Many2many('hr.employee.document', 'doc_attachment_id', 'attach_id3', 'doc_id',
                                      string="Attachment", invisible=1)
