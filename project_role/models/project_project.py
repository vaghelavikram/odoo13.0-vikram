# -*- coding: utf-8 -*-

from odoo import fields, models, api
from datetime import datetime


class ProjectProject(models.Model):
    _inherit = 'project.project'

    @api.depends('assignment_ids')
    def _compute_assignment_count(self):
        for rec in self:
            alloc = []
            assgn = self.env['project.assignment'].sudo().search([('project_id', '=', rec.id), ('start_date', '<=', datetime.today().date()), ('end_date', '>=', datetime.today().date()), ('assign_status', '=', 'confirmed')])
            for i in assgn:
                if i.employee_id:
                    alloc.append(i.employee_id)
            rec.assignment_count = len(list(set(alloc))) if alloc else len(assgn)
            rec.allocation_count = len(list(set(alloc))) if alloc else len(assgn)

    @api.depends('assignment_ids')
    def _compute_emp_allocation(self):
        today = fields.Date.today()
        for rec in self:
            active_allocation = [allocation for allocation in rec.assignment_ids if allocation.end_date and allocation.end_date >= today and not allocation.allocation_completed and allocation.assign_status == 'confirmed']
            inactive_allocation = [allocation.employee_id.id for allocation in rec.assignment_ids if allocation.end_date and (allocation.end_date < today or allocation.allocation_completed) and allocation.assign_status == 'confirmed']
            active_employees = [active.employee_id.id for active in active_allocation if active.employee_id.id not in inactive_allocation]
            rec.active_allocation_ids = active_employees
            rec.active_emp = rec.active_allocation_ids

    def _add_domain(self):
        emp_child_ids = []
        for rec in self:
            emp_obj = self.env['hr.employee'].search([('parent_id', '=', rec.env.user.id)])
            if emp_obj:
                emp_child_ids.append(emp_obj.id)
        user_obj_ids = []
        for emp in emp_child_ids:
            user_obj = self.env['res.users'].search([('id','=', emp.user_id)])
            if user_obj:
                user_obj_ids.append(user_obj.id)
        if len(user_obj_ids) > 0:
            return user_obj_ids
        else:
            return []

    assignment_ids = fields.One2many(
        string='Project Assignments',
        comodel_name='project.assignment',
        inverse_name='project_id',
        tracking=True,
    )
    assignment_count = fields.Integer(string="Assignment Count", compute="_compute_assignment_count")
    allocation_count = fields.Integer(string="Allocation Count")
    active_allocation_ids = fields.Many2many('hr.employee', string="Active Allocation Emp", compute="_compute_emp_allocation")
    active_emp = fields.Many2many('hr.employee', string="Active Allocations")

    office_location = fields.Text(string="Office Location from where project is being executed")
    name_of_client_organizations_country = fields.Text(string="Name of Client organization's country")
    client_data_stored_location = fields.Text(string="Where is the client data stored")
    loc_source_code = fields.Text(string="Location of source code & Servers")
    system_accessed = fields.Text(
        string="How the systems (Stage / Prod / UAT) are accessed where live/actual data possibily resides?")
    dev_system_accessed = fields.Text(string="How the systems (Dev / Test /Sourcecode etc) are accessed ")
    resource_access_control = fields.Text(
        string="Access Control : Which  resources can access PHI/ePHI Identifiable Information.")
    received_phi_ephi_identifiable_information = fields.Text(
        string="How is the PHI/ePHI Identifiable Information received from the client / data subject (If applicable)")
    shared_phi_ephi_identifiable_information = fields.Text(
        string="How is the PHI/ePHI Identifiable Information shared with client / data subject (If applicable)")
    data_processing = fields.Text(string="Data processing carried out",
                                  help="e.g. Collection, Storage, Recording, Structuring, alteration, communication, "
                                       "sharing with other functions/projects")
    third_country_name = fields.Text(string="Transfer to third country or international organization (country name)",
                                     help="Please mention name of the third country or the organization where the "
                                          "data is transferred")
    general_description = fields.Text(
        string="General description of the technical and organisational security measures",
        help="e.g. Password protection to files, encryption of laptop hard drives, "
             "AWS storage with restricted access, etc.")
    project_piiline_ids = fields.One2many('project.piiline', 'project_id', string='PII/ePHI Register')
    user_ids_project = fields.Many2many('res.users', string="project_user_ids", domain=_add_domain)

    def write(self, vals):
        res = super(ProjectProject, self).write(vals)
        if 'user_ids_project' in vals:
            res_group_users = self.env['res.groups'].sudo().search([('name', '=', 'Role: Project Coordinator')]).users
            if res_group_users:
                self.env['res.groups'].sudo().search([('name', '=', 'Role: Project Coordinator')]).users = [(6, 0, [])]
            gid = self.env['res.groups'].sudo().search([('name', '=', 'Role: Project Coordinator')]).id
            for user in vals['user_ids_project'][0][2]:
                uid = self.env['res.users'].sudo().search([('id', '=', user)]).id
                if uid and gid:
                    res_group = self.env['res.groups'].sudo().search([('name', '=', 'Role: Project Coordinator')])
                    res_group.users = [(4, uid)]
        return res




    # @api.depends('user_ids_project')
    # def _compute_user_ids(self):
    #     print(self.active_emp)
        # u = self.search([('user_id', '=', self.active_emp.parent_id)])
        # print(u)
        # user_ids_project = False
        # return {}
        # for rec in self:
        #     emp_records = self.env['hr.employee'].search([('parent_id', '=', rec.env.user.id)])
        # if emp_records:
        #     for emp in emp_records:
        #         if emp.user_id:
        #             user_ids_projects += emp.user_id
        # emp_records1 = self.env['hr.employee'].filtered(lambda x: x.parent_id == self.env.user.id).mapped('user_id')
        # emp_records1 = emp_records1.mapped('user_id')
        # print(emp_records)
        # print(emp_records1)
        # return
        # l=[]
        # for rec in self:
        #     ("partner_id", "child_of", record.id)
        # for rec in u:
        #         print("rec", rec)
        #         print(rec.user_id)
        #         if rec.user_id:
        #     l.append(rec.user_id)
        #     print(emp_records)
        #     print(type(emp_records))
        #     # return l
        #     # return emp_records
        #         print("l", l)
        #         if l:
        #         else:
        #             return {'domain': {'user_ids_project': []}}

class ProjectPIILine(models.Model):
    _name = 'project.piiline'

    group_team_member_name = fields.Char(string='Group/Team Member Name')
    name = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Name')
    date_of_birth = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Date of Birth')
    telephone_numbers = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Telephone Numbers')
    geographic_data = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Geographic data')
    fax_numbers = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'FAX Numbers')
    social_security_numbers = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Social Security Numbers')
    email_addresses = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Email Addresses')
    medical_records = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Medical Records')
    bank_account_numbers = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Bank Account Numbers')
    health_plan_beneficiary_numbers = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                                       'Health Plan Beneficiary Numbers')
    certificate_license_numbers = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Certificate/ license Numbers')
    vehicle_identifiers_serial_numbers_including_license_plates = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                                                                   'Vehicle identifiers and serial '
                                                                                   'numbers including license plates')
    web_urls = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Web URLs')
    device_identifiers_serial_numbers = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Device Identifiers and '
                                                                                         'Serial Numbers')
    internet_protocol_addresses = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Internet Protocol Addresses ')
    full_face_photos_comparable_images = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Full Face Photos and '
                                                                                          'Comparable Images')
    biometric_identifiers = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Biometric Identifiers')
    any_unique_identifying_number_code = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Any Unique Identifying '
                                                                                          'Number or Code')
    any_other_field = fields.Text(string='Any Other Field')
    project_id = fields.Many2one('project.project', string='Project')
