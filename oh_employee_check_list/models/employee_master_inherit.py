# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class EmployeeEntryDocuments(models.Model):
    _name = 'employee.checklist'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "e-Zestian Documents"

    def name_get(self):
        result = []
        for each in self:
            if each.document_type == 'entry':
                name = each.name
            elif each.document_type == 'exit':
                name = each.name
            elif each.document_type == 'other':
                name = each.name
            elif each.document_type == 'confirmation':
                name = each.name
            result.append((each.id, name))
        return result

    name = fields.Char(string='Name', copy=False, required=1)
    document_type = fields.Selection([('entry', 'Entry Process'),
                                      ('exit', 'Exit Process'),
                                      ('other', 'Optional'),
                                      ('confirmation', 'Confirmation Process')], string='Checklist Type',
                                     help='Type of Checklist', readonly=1, required=1)
    company_id = fields.Many2many('res.company', string="Company", groups="base.group_multi_company")
    entry_obj = fields.Many2many('hr.employee', 'entry_checklist', 'hr_check_rel', 'check_hr_rel',
                                 invisible=1)
    exit_obj = fields.Many2many('hr.employee', 'exit_checklist', 'hr_exit_rel', 'exit_hr_rel',
                                invisible=1)

class HrEmployeeDocumentInherit(models.Model):
    _inherit = 'hr.employee.document'
    _rec_name = 'employee_ref'

    @api.model
    def create(self, vals):
        # extn = vals.get('doc_filename').split('.')[-1]
        # employee = self.env['hr.employee'].browse(vals.get('employee_ref'))
        # if employee:
        #     employee_barcode = employee.barcode
        #     employee_name = employee.name.split(' ')[0].lower()
        #     filename = employee_barcode + '_' + employee_name
        #     checklist_name = self.env['employee.checklist'].search([('id', '=', vals.get('document_name'))])
        #     if checklist_name:
        #         doc_name = '_'.join(checklist_name.name.lower().split(' (')[0].split(' '))
        #         filename = employee_barcode + '_' + employee_name + '_' + doc_name + '.' + extn
        #         vals['doc_filename'] = filename

        result = super(HrEmployeeDocumentInherit, self).create(vals)
        if result.document_name.document_type == 'entry':
            result.employee_ref.write({'entry_checklist': [(4, result.document_name.id)]})
        if result.document_name.document_type == 'exit':
            result.employee_ref.write({'exit_checklist': [(4, result.document_name.id)]})
        if result.document_name.document_type == 'other':
            result.employee_ref.write({'other_checklist': [(4, result.document_name.id)]})
        return result

    # def write(self, vals):
    #     document_name = vals.get('document_name') or self.document_name.id
    #     if vals.get('doc_filename'):
    #         extn = vals.get('doc_filename').split('.')[-1]
    #         employee_barcode = self.employee_ref.barcode
    #         employee_name = self.employee_ref.name.split(' ')[0].lower()
    #         filename = employee_barcode + '_' + employee_name
    #         checklist_name = self.env['employee.checklist'].search([('id', '=', document_name)])
    #         if checklist_name:
    #             doc_name = '_'.join(checklist_name.name.lower().split(' (')[0].split(' '))
    #             filename = employee_barcode + '_' + employee_name + '_' + doc_name + '.' + extn
    #             vals['doc_filename'] = filename
    #     return super(HrEmployeeDocumentInherit, self).write(vals)

    def unlink(self):
        for result in self:
            if result.document_name.document_type == 'entry':
                result.employee_ref.write({'entry_checklist': [(3, result.document_name.id)]})
            if result.document_name.document_type == 'exit':
                result.employee_ref.write({'exit_checklist': [(3, result.document_name.id)]})
            if result.document_name.document_type == 'other':
                result.employee_ref.write({'other_checklist': [(3, result.document_name.id)]})
        res = super(HrEmployeeDocumentInherit, self).unlink()
        return res

    @api.depends('employee_ref', 'document_name')
    def _get_file_name(self):
        for rec in self:
            if rec.employee_ref:
                employee_barcode = rec.employee_ref.barcode
                employee_name = rec.employee_ref.name.split(' ')[0].lower()
                filename = employee_barcode + '_' + employee_name
                if rec.document_name:
                    checklist_name = self.env['employee.checklist'].search([('id', '=', rec.document_name.id)])
                    doc_name = '_'.join(checklist_name.name.lower().split(' (')[0].split(' '))
                    filename = employee_barcode + '_' + employee_name + '_' + doc_name
                rec.doc_filename = filename
            else:
                rec.doc_filename = "Attachment"

    document_name = fields.Many2one('employee.checklist', string='Document', help='Type of Document', required=True)
    doc_filename = fields.Char(string="Filename", compute="_get_file_name")


class EmployeeMasterInherit(models.Model):
    _inherit = 'hr.employee'

    @api.depends('exit_checklist')
    def exit_progress(self):
        for each in self:
            total_len = self.env['employee.checklist'].search_count([('document_type', '=', 'exit'), ('company_id', '=', self.company_id.id)])
            entry_len = len(each.exit_checklist)
            if total_len != 0:
                each.exit_progress = (entry_len * 100) / total_len
            else:
                each.exit_progress = 0

    @api.depends('entry_checklist')
    def entry_progress(self):
        for each in self:
            total_len = self.env['employee.checklist'].search_count([('document_type', '=', 'entry'), ('company_id', '=', each.company_id.id), ('emp_category_ids', '=', each.employee_category.id)])
            entry_len = len(each.entry_checklist)
            if total_len != 0:
                each.entry_progress = (entry_len*100) / total_len
            else:
                each.entry_progress = 0

    def get_domain_emp(self):
        domain = (('document_type', '=', 'entry'),)
        if not self.env.user.user_has_groups('hr.group_hr_user'):
            if self.env.user.employee_id and self.env.user.employee_id.employee_category:
                domain += (('emp_category_ids', '=', self.env.user.employee_id.employee_category.id),)
        return domain

    entry_checklist = fields.Many2many('employee.checklist', 'entry_obj', 'check_hr_rel', 'hr_check_rel',
                                       string='Entry Process',
                                       domain=lambda self: self.get_domain_emp())
    exit_checklist = fields.Many2many('employee.checklist', 'exit_obj', 'exit_hr_rel', 'hr_exit_rel',
                                      string='Exit Process',
                                      domain=[('document_type', '=', 'exit')])
    other_checklist = fields.Many2many('employee.checklist', 'other_obj', 'other_hr_rel', 'hr_other_rel',
                                      string='Optional Checklist',
                                      domain=[('document_type', '=', 'other')])
    confirmation_checklist = fields.Many2many('employee.checklist', 'confirmation_obj', 'confirmation_hr_rel', 'hr_confirmation_rel',
                                      string='Confirmation Checklist',
                                      domain=[('document_type', '=', 'confirmation')])
    entry_progress = fields.Float(compute=entry_progress, string='Entry Progress', store=True, default=0.0)
    exit_progress = fields.Float(compute=exit_progress, string='Exit Progress', store=True, default=0.0)
    maximum_rate = fields.Integer(default=100)
    check_list_enable = fields.Boolean(invisible=True, copy=False)
    employee_category = fields.Many2one("hr.contract.type", track_visibility="onchange", string="Team Member Category")


# class EmployeeDocumentInherit(models.Model):
#     _inherit = 'hr.employee.document'

#     @api.model
#     def create(self, vals):
#         result = super(EmployeeDocumentInherit, self).create(vals)
#         if result.document_name.document_type == 'entry':
#             result.employee_ref.write({'entry_checklist': [(4, result.document_name.id)]})
#         if result.document_name.document_type == 'exit':
#             result.employee_ref.write({'exit_checklist': [(4, result.document_name.id)]})
#         if result.document_name.document_type == 'other':
#             result.employee_ref.write({'other_checklist': [(4, result.document_name.id)]})
        # if type(vals.get('doc_attachment_id')[0]) == 'list' and len(vals.get('doc_attachment_id')[0]) > 1:
        # import pdb; pdb.set_trace()
        # document = vals.get('doc_attachment_id')[0][2]
        # for rec in document:
        #     file = self.env['ir.attachment'].browse(rec)
        #     if file:
        #         file_extn = file.name.split('.')[-1].lower()
        #         employee_id = self.env['hr.employee'].search([('id','=',vals.get('employee_ref'))])
        #         if employee_id:
        #             employee_barcode = employee_id.barcode
        #             employee_name = employee_id.name.split(' ')[0].lower()
        #             checklist_name = self.env['employee.checklist'].search([('id','=',vals['document_name'])])
        #             doc_name = '_'.join(checklist_name.name.lower().split(' (')[0].split(' '))
        #             file.name = employee_barcode + '_' + employee_name + '_' + doc_name + '.' + file_extn
        # doc_file_type = self.env['document.file.type'].search([('name', '=', file_extn)])
        # if not doc_file_type:
        #     raise UserError(_("This %s file is not supported." % file_extn.upper()))
        # # check the size only when we upload a file.
        # file_size = self.env['ir.config_parameter'].sudo().get_param('oh_employee_check_list.file_size')
        # if (file.file_size / 1024.0 / 1024.0) > (int(file_size) or 5):
        #     raise UserError(_('File %s is too big. File size cannot exceed %sMB' % (file.name,int(file_size))))
        # return result

    # def write(self, vals):
    #     result = super(EmployeeDocumentInherit, self).write(vals)
    #     employee_id = self.env['hr.employee'].search([('id','=',self.employee_ref.id)])
    #     employee_barcode = employee_id.barcode
    #     employee_name = employee_id.name.split(' ')[0].lower()
    #     document = vals.get('doc_attachment_id')
    #     if document:
    #         document = document[0][2]
    #         for rec in document:
    #             file = self.env['ir.attachment'].browse(rec)
    #             if file:
    #                 file_extn = file.name.split('.')[-1].lower()
    #                 doc_file_type = self.env['document.file.type'].search([('name', '=', file_extn)])
    #                 if not doc_file_type:
    #                     raise UserError(_("This %s file is not supported." % file_extn.upper()))
    #                 # check the size only when we upload a file.
    #                 file_size = self.env['ir.config_parameter'].sudo().get_param('oh_employee_check_list.file_size')
    #                 if (file.file_size / 1024.0 / 1024.0) > (int(file_size) or 5):
    #                     raise UserError(_('File %s is too big. File size cannot exceed %sMB' % (file.name,int(file_size))))
    #                 if 'doc_attachment_id' in vals and 'document_name' in vals:
    #                     checklist_name = self.env['employee.checklist'].search([('id','=',vals['document_name'])])
    #                     doc_name = '_'.join(checklist_name.name.lower().split(' (')[0].split(' '))
    #                     file.name = employee_barcode + '_' + employee_name + '_' + doc_name + '.' + file_extn
    #                 elif 'doc_attachment_id' in vals and not 'document_name' in vals:
    #                     doc_name = '_'.join(self.document_name.name.lower().split(' (')[0].split(' '))
    #                     file.name = employee_barcode + '_' + employee_name + '_' + doc_name + '.' + file_extn
    #     return result
