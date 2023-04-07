# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta, date
from odoo.exceptions import UserError


class HRPayrollLocation(models.Model):
    _name = 'hr.payroll.location'
    _description = "HR Payroll Location"

    name = fields.Char(string='Payroll Location')

class ProjectManagementInherit(models.Model):
    _inherit = 'project.project'

    @api.model
    def create(self, vals):
        # assigning the sequence for the record
        kth_id = self.env['hr.payroll.location'].sudo().search([('name', '=', 'KTH')]).id
        sez3_id = self.env['hr.payroll.location'].sudo().search([('name', '=', 'SEZ 3')]).id
        sez6_id = self.env['hr.payroll.location'].sudo().search([('name', '=', 'SEZ 6')]).id
        contract_id = self.env['hr.payroll.location'].sudo().search([('name', 'in', ['On Contract'])]).id
        inc_id = self.env['hr.payroll.location'].sudo().search([('name', 'in', ['Inc USA', 'On Contract INC'])]).ids
        gmbh_id = self.env['hr.payroll.location'].sudo().search([('name', 'in', ['GMBH Payroll', 'On Contract GMBH'])]).ids
        uk_id = self.env['hr.payroll.location'].sudo().search([('name', 'in', ['UK Payroll', 'On Contract UK'])]).ids
        austria_id = self.env['hr.payroll.location'].sudo().search([('name', 'in', ['Austria Branch Office', 'On Contract Austria'])]).ids
        abbrvted_name = vals.get('abbreviated_name', _('New'))
        if vals.get('name_seq', ('New')) == ('New'):
            vals['name_seq'] = self.env['ir.sequence'].next_by_code('project.mgmt.sequence') or _('New')
        if vals.get('payroll_loc') == kth_id:
            if abbrvted_name == _('New'):
                vals['abbreviated_name'] = self.env['ir.sequence'].next_by_code('kth.location') or _('New')
        if vals.get('payroll_loc') == sez3_id:
            if abbrvted_name == _('New'):
                vals['abbreviated_name'] = self.env['ir.sequence'].next_by_code('sez3.location') or _('New')
        if vals.get('payroll_loc') == sez6_id:
            if abbrvted_name == _('New'):
                vals['abbreviated_name'] = self.env['ir.sequence'].next_by_code('sez6.location') or _('New')
        if vals.get('payroll_loc') == contract_id:
            if abbrvted_name == _('New'):
                vals['abbreviated_name'] = self.env['ir.sequence'].next_by_code('contract.location') or _('New')
        if vals.get('payroll_loc') in inc_id:
            if abbrvted_name == _('New'):
                vals['abbreviated_name'] = self.env['ir.sequence'].next_by_code('inc.location') or _('New')
        if vals.get('payroll_loc') in gmbh_id:
            if abbrvted_name == _('New'):
                vals['abbreviated_name'] = self.env['ir.sequence'].next_by_code('gmbh.location') or _('New')
        if vals.get('payroll_loc') in uk_id:
            if abbrvted_name == _('New'):
                vals['abbreviated_name'] = self.env['ir.sequence'].next_by_code('uk.location') or _('New')
        if vals.get('payroll_loc') in austria_id:
            if abbrvted_name == _('New'):
                vals['abbreviated_name'] = self.env['ir.sequence'].next_by_code('austria.location') or _('New')
        if vals.get('sale_order_id'):
            order_id = self.env['sale.order'].sudo().search([('id', '=', vals.get('sale_order_id'))]).name
        else:
            order_id = ''
        # vals['name'] = vals.get('name') + ' ' + (vals.get('abbreviated_name') or '') + ' [' + (vals.get('name_seq') or '') + '/' + str(order_id) + ']'
        res = super(ProjectManagementInherit, self).create(vals)
        return res

    def write(self, vals):
        # assigning the sequence for the record
        kth_id = self.env['hr.payroll.location'].sudo().search([('name', '=', 'KTH')]).id
        sez3_id = self.env['hr.payroll.location'].sudo().search([('name', '=', 'SEZ 3')]).id
        sez6_id = self.env['hr.payroll.location'].sudo().search([('name', '=', 'SEZ 6')]).id
        contract_id = self.env['hr.payroll.location'].sudo().search([('name', 'in', ['On Contract'])]).id
        inc_id = self.env['hr.payroll.location'].sudo().search([('name', 'in', ['Inc USA', 'On Contract INC'])]).ids
        gmbh_id = self.env['hr.payroll.location'].sudo().search([('name', 'in', ['GMBH Payroll', 'On Contract GMBH'])]).ids
        uk_id = self.env['hr.payroll.location'].sudo().search([('name', 'in', ['UK Payroll', 'On Contract UK'])]).ids
        austria_id = self.env['hr.payroll.location'].sudo().search([('name', 'in', ['Austria Branch Office', 'On Contract Austria'])]).ids
        if vals.get('payroll_loc') == kth_id:
            if self.abbreviated_name == _('New'):
                self.abbreviated_name = self.env['ir.sequence'].next_by_code('kth.location') or _('New')
                # self.name = self.abbreviated_name + self.name
        if vals.get('payroll_loc') == sez3_id:
            if self.abbreviated_name == _('New'):
                self.abbreviated_name = self.env['ir.sequence'].next_by_code('sez3.location') or _('New')
                # self.name = self.abbreviated_name + self.name
        if vals.get('payroll_loc') == sez6_id:
            if self.abbreviated_name == _('New'):
                self.abbreviated_name = self.env['ir.sequence'].next_by_code('sez6.location') or _('New')
                # self.name = self.abbreviated_name + self.name
        if vals.get('payroll_loc') == contract_id:
            if self.abbreviated_name == _('New'):
                self.abbreviated_name = self.env['ir.sequence'].next_by_code('contract.location') or _('New')
                # self.name = self.abbreviated_name + self.name
        if vals.get('payroll_loc') in inc_id:
            if self.abbreviated_name == _('New'):
                vals['abbreviated_name'] = self.env['ir.sequence'].next_by_code('inc.location') or _('New')
        if vals.get('payroll_loc') in gmbh_id:
            if self.abbreviated_name == _('New'):
                vals['abbreviated_name'] = self.env['ir.sequence'].next_by_code('gmbh.location') or _('New')
        if vals.get('payroll_loc') in uk_id:
            if self.abbreviated_name == _('New'):
                vals['abbreviated_name'] = self.env['ir.sequence'].next_by_code('uk.location') or _('New')
        if vals.get('payroll_loc') in austria_id:
            if self.abbreviated_name == _('New'):
                vals['abbreviated_name'] = self.env['ir.sequence'].next_by_code('austria.location') or _('New')
        if vals.get('actual_end_date'):
            allocation = [i for i in self.assignment_ids if i.end_date == self.actual_end_date and i.allocation_completed]
            for alloc in allocation:
                alloc.end_date = vals.get('actual_end_date')
        # if vals.get('sale_order_id'):
        #     order_id = self.env['sale.order'].search([('id', '=', vals.get('sale_order_id'))]).name
        #     self.name = self.abbreviated_name + ' [' + self.name_seq + '/' + order_id + ']'
        res = super(ProjectManagementInherit, self).write(vals)
        return res

    def name_get(self):
        result = []
        for project in self:
            if self._context.get('show_detail'):
                name = project.name + ' (' + project.name_seq + '[' + project.abbreviated_name + ']' + ')'
                result.append((project.id, name))
            else:
                result.append((project.id, project.name))
        return result

    def action_allocation(self):
        self.is_manager_allocate = True
        view_form_id = self.env.ref('project_role.project_assignment_form').id
        action = {
            'name': _('Allocations'),
            'type': 'ir.actions.act_window',
            'res_model': 'project.assignment',
            'view_mode': 'form',
            'views': [(view_form_id, 'form')],
            'target': 'new',
            'context': {
                        'default_employee_id': self.user_id.employee_id.id if self.user_id else False,
                        'default_project_role_id': self.env['hr.job'].search([('name', '=', 'Project Manager')], limit=1).id,
                        'default_project_id': self.id,
                        'default_start_date': self.actual_start_date,
                        'default_end_date': self.planned_end_date
                    }
        }
        return action

    def _get_sale_order_line(self):
        for rec in self:
            sale_order_ids = self.env['sale.order.line'].search([
                ('is_expense', '=', False),
                ('order_id', '=', rec.sale_order_id.id),
                ('state', 'in', ['sale', 'done'])
            ])
            rec.sale_line_ids = sale_order_ids.ids

    def _get_days(self):
        for rec in self:
            if rec.planned_end_date and rec.planned_start_date:
                rec.duration = (rec.planned_end_date - rec.planned_start_date).days
            else:
                rec.duration = False

    @api.depends('user_id')
    def _check_user_group(self):
        for rec in self:
            user = self.env.user
            check_group = user.user_has_groups('project_mgmt.group_project_operations')
            if check_group or user.user_has_groups('project_mgmt.group_project_manager_create') or user.user_has_groups('project_mgmt.group_project_operations_copy'):
                rec.edit_project_access = True
            else:
                rec.edit_project_access = False

    @api.depends('user_id')
    def _check_ryg_access(self):
        for rec in self:
            ids = [alloc.employee_id.user_id.id for alloc in rec.assignment_ids if alloc.show_ryg == True]
            ids.append(rec.user_id.id)
            if rec.department_id:
                if rec.department_id.custom_manager_id:
                    ids.append(rec.department_id.custom_manager_id.user_id.id)
                department = rec.department_id
                if department.parent_id and 'Operations' in department.complete_name:
                    while department.parent_id.name != 'Operations':
                        department = department.parent_id
                        if department.custom_manager_id:
                            ids.append(department.custom_manager_id.user_id.id)
                    if department.parent_id.name == 'Operations':
                        if department.custom_manager_id:
                            ids.append(department.custom_manager_id.user_id.id)
            user = self.env.user
            if user.id in ids or user.user_has_groups('project_mgmt.group_project_operations') or user.user_has_groups('project_mgmt.group_project_operations_copy'):
                rec.ryg_access = True
            else:
                rec.ryg_access = False

    @api.depends('sale_order_id')
    def _get_invoice_count(self):
        for order in self:
            invoices = order.sale_order_id.order_line.invoice_lines.move_id.filtered(lambda r: r.type in ('out_invoice', 'out_refund'))
            order.invoice_count = len(invoices)

    @api.onchange('is_internal')
    def _onchange_is_internal(self):
        res = {}
        if self.is_internal:
            self.partner_id = self.env.company.id
            self.practice = self.env['project.whizible.practice'].search([('name', 'ilike', 'Enabling Process')], limit=1).id
            res['domain'] = {'department_id': []}
        else:
            res['domain'] = {'department_id': [('parent_id', 'child_of', 'Operations')]}
        return res

    def action_view_invoice(self):
        invoices = self.sale_order_id.mapped('invoice_ids')
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        action['domain'] = [('id', 'in', invoices.ids)]
        return action

    def action_submit_charter(self):
        self.is_submit = True
        duhead = self.du_head_id.id
        du_head_email = self.env['hr.employee'].sudo().search([('user_id','=',duhead)])
        email_to = []
        if du_head_email:
            head_email = du_head_email.work_email
            if head_email:
                email_to.append(head_email)
        qa_team_email = 'qa-team@e-zest.in'
        email_to.append(qa_team_email)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        message_body = '<p>Hi,</p><br/>\
                    <p>Charter for Project {0} is completed by {1}.</p>\
                    <br/><br/>\
                    <br/>Kindly Approve<br/>' \
                       'Click on <a href="{2}/web#id={3}&amp;model=project.project&amp;view_type=form&amp;cids=1" target="_blank" style="background-color: #875A7B; padding: 8px 16px 8px 16px; text-decoration: none; color: #fff; border-radius: 5px; font-size:13px;">\
                    View Charter </a> for further process\
                    <br><br/>\
                    Thanks,\
                    <br/>\
                    Team Unity\
                    <p><br></p>'.format(str(self.name), str(self.env.user.name), base_url, int(self.id))
        for user in self.env['sale.operation.team'].search([('department_id', '=', self.sale_order_id.sbu_id.id), ('company_id', '=', self.company_id.id)]):
            email_to.append(user.user_id.login)
            if user.email_text:
                email_to.append(user.email_text)
        self.env['mail.mail'].create({
            'subject': '%s submitted Project charter for %s' % (self.env.user.name, self.name),
            'body_html': message_body,
            'email_from': 'unity@e-zest.in',
            'email_to': ','.join(i for i in email_to),
            'email_cc': 'unity@e-zest.in'
        }).sudo().send()

    def action_approve_charter(self):
        duhead = self.du_head_id.id
        du_head_rec = self.env['hr.employee'].sudo().search([('user_id', '=', duhead)])
        email_to = []
        du_head_name = ''
        if du_head_rec:
            head_email = du_head_rec.work_email
            du_head_name= du_head_rec.name
            if head_email:
                email_to.append(head_email)
        qa_team_email = 'qa-team@e-zest.in'
        email_to.append(qa_team_email)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        message_body = '<p>Hi,</p><br/>\
                            <p>Charter for Project {0} is approved by {1}.</p>\
                            <br/><br/>\
                            <br/>Kindly Approve<br/>Click on <a href="{2}/web#id={3}&amp;model=project.project&amp;view_type=form&amp;cids=1" target="_blank" style="background-color: #875A7B; padding: 8px 16px 8px 16px; text-decoration: none; color: #fff; border-radius: 5px; font-size:13px;">\
                            View Charter </a> for further process\
                            <br><br/>\
                            Thanks,\
                            <br/>\
                            Team Unity\
                            <p><br></p>'.format(str(self.name), str(du_head_name), base_url, int(self.id))
        for user in self.env['sale.operation.team'].search(
                [('department_id', '=', self.sale_order_id.sbu_id.id), ('company_id', '=', self.company_id.id)]):
            email_to.append(user.user_id.login)
            if user.email_text:
                email_to.append(user.email_text)
        self.env['mail.mail'].create({
            'subject': 'Project charter Approval for %s' % (self.name),
            'body_html': message_body,
            'email_from': 'unity@e-zest.in',
            'email_to': ','.join(i for i in email_to),
            'email_cc': 'unity@e-zest.in'
        }).sudo().send()

    @api.depends('department_id')
    def _get_parent_dept(self):
        for rec in self:
            if rec.department_id and ' Operations ' in rec.department_id.display_name.split('/'):
                department = rec.department_id
                if department.parent_id:
                    while department.parent_id.name != 'Operations':
                        department = department.parent_id
                rec.sbu_id = department.id
            else:
                rec.sbu_id = False

    @api.depends('sale_order_id')
    def _get_group_company_billing_location(self):
        for rec in self:
            rec.group_company_payroll_loc = False
            if rec.sale_order_id and rec.sale_order_id.group_multi_company is False and rec.sale_order_id.contract_sale_order:
                rec.group_company_payroll_loc = rec.sale_order_id.contract_sale_order.payroll_loc.id

    def _default_plans_ids(self):
        roles = {'pm': 'Project Manager', 'sd': 'Software Developer', 'qa': 'QA / Tester'} 
        vals = [(0, 0, {'role': roles[n]}) for n in roles]
        return vals

    @api.depends('sale_order_id')
    def _compute_del_eng_model(self):
        for order in self:
            order.update({
                'del_eng_model': order.sale_order_id.del_eng_model.id
            })

    @api.depends('du_head_id')
    def _compute_is_du_head(self):
        for project in self:
            if project.sudo().du_head_id:
                if self.env.user.id == project.sudo().du_head_id.id:
                    project.sudo().is_du_head = True
                else:
                    project.sudo().is_du_head = False
            else:
                project.sudo().is_du_head= False


    whizible_id = fields.Char(string='Whizible Project Id', tracking=True)
    abbreviated_name = fields.Char(string='Abbreviated Name', default='New', tracking=True)
    customer_type = fields.Selection([('new_logo', 'NEW LOGO'),
         ('new', 'NEW NEW'),
         ('existing', 'EXISTING')], string="Customer Type")
    project_type = fields.Selection([
         ('new', 'NEW'),
         ('existing', 'EXISTING')], string="Project Type")
    user_id = fields.Many2one('res.users', string='Project Manager', tracking=True, domain="[('company_id', '=', company_id)]")
    commercial_details = fields.Selection([('tnm', 'Time & Material'), ('fixed_cost', 'Fixed Cost')], string='Pricing Model')
    description = fields.Text(string='Description')
    work_hours = fields.Float(string="Budgeted Hours")
    duration = fields.Integer(string='Duration(days)', compute="_get_days")
    project_value = fields.Float(string="Project Value")
    project_ref = fields.Char(string='Work Order Reference')
    ryg_review = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='RYG Review')
    project_size = fields.Integer(string="Project Size", help="e.g. size in Story points/Use case points/Complexity Points")
    project_size_char = fields.Char(string="Project Size", help="e.g. size in Story points/Use case points/Complexity Points")
    project_status = fields.Many2one('project.whizible.status', string='Project Status', tracking=True)
    life_cycle = fields.Many2one('project.whizible.life', string='Life Cycle', tracking=True, help="e.g. Agile scrum, Kanban, Waterfall, Prince2, etc.")
    project_currency = fields.Many2one('res.currency', string='Project Currency', tracking=True)
    project_pricelist = fields.Many2one('product.pricelist', string='Project Currency')
    practice = fields.Many2one('project.whizible.practice', string='Project Practice')
    organization_unit = fields.Many2one('project.whizible.organization', string='Delivery Unit', tracking=True)
    geo_location = fields.Many2one('geo.location', string='Geo Location', tracking=True)
    # del_eng_model = fields.Many2one('del.engagemodel',string="Delivery Engagement model", related='sale_order_id.del_eng_model')
    del_eng_model = fields.Many2one('del.engagemodel',string="Delivery Engagement model", compute='_compute_del_eng_model')
    edit_project_access = fields.Boolean(string="Project Access", compute="_check_user_group")
    ryg_access = fields.Boolean(string="RYG Access", compute="_check_ryg_access")
    delivery_responsible = fields.Selection([('ezest', 'e-Zest'), ('client', 'Client')], string=" Delivery Responsibility")
    # commercial_details = fields.Many2one('project.whizible.commercial', string='Commercial Details')
    billable = fields.Boolean(string='Billable', default=True)
    is_internal = fields.Boolean(string='Is Internal', default=False)
    planned_start_date = fields.Date('Planned Start Date', required=True, tracking=True)
    planned_end_date = fields.Date(string="Planned End Date", required=True, tracking=True)
    actual_start_date = fields.Date(string="Actual Start Date", tracking=True)
    actual_end_date = fields.Date(string="Actual End Date", tracking=True)
    name_seq = fields.Char(string='Unity ID', copy=False, readonly=True, tracking=True, default='New')
    payroll_loc = fields.Many2one('hr.payroll.location', string='Billing Location', required=True, tracking=True)
    group_company_payroll_loc = fields.Many2one('hr.payroll.location', string='Group Billing Location', compute="_get_group_company_billing_location")
    work_loc = fields.Many2one('hr.location.work', string='Work Location', tracking=True)
    project_location = fields.Many2one('project.location', string="Project Location")
    business_entity = fields.Many2one('res.company', string='Business Group', tracking=True)
    project_skill_ids = fields.One2many('hr.employee.skill', 'project_id', string="Skills")
    customer_id = fields.Many2one('res.partner', string='Customer', tracking=True)
    department_id = fields.Many2one('hr.department', 'Department', required=True, tracking=True)
    sbu_id = fields.Many2one('hr.department', 'SBU', compute="_get_parent_dept", store=True, compute_sudo=True)
    ryg_id = fields.Many2many('project.ryg', string='RYG', readonly=False)
    state = fields.Selection([
            ('draft', 'Planned'),
            ('active', 'Approved'),
            ('on_hold', 'On Hold'),
            ('closed', 'Closed'),
        ], string='Status', readonly=True, default='draft', tracking=True)
    invoice_count = fields.Integer(string='Invoice Count', compute='_get_invoice_count', readonly=True)
    primary_skill = fields.Many2one('hr.primary.skill', string="Technology")
    sale_line_ids = fields.Many2many('sale.order.line', compute="_get_sale_order_line")
    partner_id = fields.Many2one('res.partner', string='Customer', auto_join=True, tracking=True, domain="[('customer_rank','>',0),('is_company', '=', True)]")
    is_manager_allocate = fields.Boolean(string="Is Manager Allocate")
    sla = fields.Text(string="SLA")
    context = fields.Text(string="Project Context & Background")
    objective = fields.Text(string="Project Objectives- Approach for implementation and Action Plan", helpd="The approach may include the methods and techniques to be used, resources needed.")
    scope = fields.Text(string="Project Scope", help="Inclusion and Exclusion")
    on_board_off_board = fields.Text(string="Project On-boarding & Off-boarding Requirements",
                                     help="Please mention if any client/contract specific requirements, "
                                          "e.g. Background verification etc.")
    issue = fields.Text(string="Issues")
    risk = fields.Text(string="Risks and Issues")
    assumption = fields.Text(string="Assumptions")
    contraint = fields.Text(string="Constraints- Approach for implementation and Action Plan", help="The approach may include the methods and techniques to be used, resources needed.")
    dependency = fields.Text(string="Dependencies- Approach for implementation and Action Plan", help="The approach may include the methods and techniques to be used, resources needed.")
    implement_approach = fields.Text(string="Approach for implementation", help="The approach may include the methods and techniques to be used, resources needed")
    action_plan = fields.Text(string="Action Plan")
    product_vision = fields.Text(string="Product Vision")
    planned_comp_date = fields.Date(string="Planned Date of completion")
    potential_costs = fields.Text(string="Potential costs", help="It may include additional resources, licenses cost, additional office space, IT infrastructure, etc.")
    potential_benefit = fields.Text(string="Potential Benefits", help="It may include any further business opportunity, cost benefits, skill enhancement, etc.")
    intellectual_property = fields.Text(string="Intellectual Property", help="List all the intellectual property of the client like documents, applications, license credentials, etc.")
    comp_climate = fields.Text(string="Competitive Climate", help="Mention if the client is acquiring similar services from any other vendors")
    long_term_need = fields.Text(string="Long Term needs", help="Mention about the need of specific team members, tools, etc.")
    profit_margin = fields.Text(string="Profit Margins")
    core_competency = fields.Text(string="Core competencies to be enhanced")
    core_competency_3_party = fields.Text(string="Core competencies needed from other third parties")
    future_trend = fields.Text(string="Future Trends")
    security_approach = fields.Text(string="Approach to Security requirements", help="Mention if the client has specifically mentioned security requirements or only e-Zest specific security checklist will be followed.")
    benifits = fields.Text(string="Expected Business Benefits")
    key_output = fields.Text(string="Key Outputs /Deliverables")
    success = fields.Text(string="Success Criteria")
    high_estimation = fields.Char(string="High Level Estimate of Project Costs")
    size = fields.Char(string="Project Size in Story points/Use case points/Complexity Points")
    est_technique = fields.Text(string="Estimation Technique", help="e.g. SMC, Three Point Estimation, Planning Poker, T-Shirt sizing, etc.")
    non_req = fields.Text(string="Non-functional Requirements", help="e.g. Security, browser support, no. of users, performance, etc.")
    end_date_poc = fields.Date(string="Expected end date of POC if applicable")
    efforts_in_person = fields.Char(string="Efforts in Person days")
    is_submit = fields.Boolean(string="Submited?")
    team_plan_ids = fields.One2many('team.plan', 'team_plan_id', string="Team Plan", help="List the required roles in the team with number and skills. Please do not add the names.", default=_default_plans_ids)
    privacy_visibility = fields.Selection([
            ('followers', "Invited e-Zestian's"),
            ('employees', "All e-Zestian's"),
            ('portal', "Portal users and all e-Zestian's"),
        ], string='Visibility', required=True,
        default='followers',
        help="Defines the visibility of the tasks of the project:\n"
                "- Invited e-Zestian's: e-Zestian's may only see the followed project and tasks.\n"
                "- All e-Zestian's: e-Zestian's may see all project and tasks.\n"
                "- Portal users and all e-Zestian's: e-Zestian's may see everything."
                "   Portal users may see project and tasks followed by.\n"
                "   them or by someone of their company.")

    du_head_id = fields.Many2one('res.users', string='DU Head', tracking=True)
    is_du_head = fields.Boolean(string="DU Head", compute='_compute_is_du_head', default=False)

    @api.constrains('actual_end_date', 'actual_start_date', 'planned_end_date', 'planned_start_date')
    def _check_date(self):
        if self.actual_start_date and self.actual_end_date and self.actual_end_date < self.actual_start_date:
            raise UserError(_("The actual start date must be anterior to the actual end date"))
        if self.planned_start_date and self.planned_end_date and self.planned_end_date < self.planned_start_date:
            raise UserError(_("The planned start date must be anterior to the planned end date"))

    def action_active(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            if rec.actual_start_date and rec.actual_end_date:
                if rec.actual_end_date < rec.actual_start_date:
                    raise UserError("Actual Start Date must be less than Actual End Date of project")
            elif not rec.actual_start_date:
                raise UserError("Actual Start Date and Actual End Date of project are blank")
            rec.state = 'active'
            message_body = '<p>Dear {0},</p><br/>\
                    <p>The below project is active in Unity. Please fill Project Charter, Risk Management and Security Checklist.</p>\
                    <p><b>Project Name:</b> {1}</p>\
                    <br/><br/>\
                    Kindly click on <a href="{2}/web#id={3}&amp;model=project.project&amp;view_type=form&amp;cids=1" target="_blank" style="background-color: #875A7B; padding: 8px 16px 8px 16px; text-decoration: none; color: #fff; border-radius: 5px; font-size:13px;">\
                    View Project </a> for further process\
                    <br><br/>\
                    Thanks,\
                    <br/>\
                    Operations Team\
                    <p><br></p>'.format(rec.user_id.name or 'None', rec.name or 'None', base_url, int(rec.id))
            email_to = rec.user_id.login if rec.user_id else 'unity@e-zest.in'
            email_cc = ['sysadmin@e-zest.in', 'qa-team@e-zest.in']
            for user in self.env['sale.operation.team'].search([('department_id', '=', rec.sale_order_id.sbu_id.id), ('company_id', '=', rec.company_id.id)]):
                email_cc.append(user.user_id.login)
                if user.email_text:
                    email_cc.append(user.email_text)
            if rec.department_id and rec.department_id.custom_manager_id:
                email_cc.append(rec.department_id.custom_manager_id.user_id.login)
            self.env['mail.mail'].create({
                'subject': 'Project Status- Active - %s' % rec.name,
                'body_html': message_body,
                'email_from': 'unity@e-zest.in',
                'email_to': email_to,
                'email_cc': ', '.join(m for m in email_cc)
            }).sudo().send()

    def action_close_project(self):
        view_id = self.env.ref('project_mgmt.close_project_form').id
        return {
            'name': _('Close Project'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'close.project',
            'view_id': view_id,
            'target': 'new',
            'context': {
                        'default_actual_start_date': self.actual_start_date,
                        'default_actual_end_date': fields.Date.today()
                    }
        }

    def action_closed(self):
        for rec in self:
            alloc = self.env['project.assignment'].search([('project_id', '=', rec.id), ('assign_status', '=', 'confirmed')])
            tag = self.env['allocation.tag'].search([('name', '=', 'Released')])
            if not tag:
                tag = self.env['allocation.tag'].create({'name': 'Released'})
            for i in alloc:
                if i.allocation_completed:
                    if not i.allocation_tags:
                        i.write({
                            'allocation_tags': [[6, False, [tag.id]]]
                        })
                elif rec.actual_end_date < i.end_date:
                    i.write({
                        'end_date': rec.actual_end_date,
                        'allocation_tags': [[6, False, [tag.id]]]
                    })
                # elif i.end_date < date.today():
                #     if not i.allocation_tags:
                #         i.write({
                #             'allocation_tags': [[6, False, [tag.id]]]
                #         })
                else:
                    i.write({
                        'end_date': rec.actual_end_date,
                        'allocation_tags': [[6, False, [tag.id]]]
                    })
            rec.state = "closed"
            multi_company_project = self.env['project.project'].search([('name', '=', rec.name), ('company_id', '!=', rec.company_id.id)])
            for projct in multi_company_project:
                projct.sudo().write({'planned_end_date': rec.actual_end_date, 'actual_end_date': rec.actual_end_date, 'state': 'closed'})
                projct.sale_order_id.sudo().write({'state': 'done'})
            rec.sale_order_id.sudo().write({'state': 'done'})
            # rec.actual_end_date = date.today()

            message_body = '<p>Dear {0},</p><br/>\
                    <p>The below project is closed in Unity.</p>\
                    <p><b>Project Name:</b> {1}</p>\
                    <p><b>Project Closed Date:</b> {2}</p>\
                    <br/><br/>\
                    <p><br></p>'.format(rec.user_id.name or 'None', rec.name or 'None', rec.actual_end_date, int(rec.id))
            message_body += '<strong>Name of Team Members Released:<strong> <br/>'
            message_body += '<table border="1" width="100%" cellpadding="0" bgcolor="#ededed">'
            message_body += '<tr style="text-align:center;">'\
                                '<th>' + 'Sr. No.' + '</th>'\
                                '<th>' + 'e-Zestian Name' + '</th>'\
                                '<th>' + 'Assigned From' + '</th>'\
                                '<th>' + 'Assigned To' + '</th>'\
                            '</tr>'
            released_count = 1
            for allocate in rec.assignment_ids.filtered(lambda self: self.end_date == rec.actual_end_date):
                message_body += '<tr style="text-align:center;">'\
                                    '<td>' + str(released_count) + '</td>'\
                                    '<td>' + str(allocate.employee_id.name) + '</td>'\
                                    '<td>' + str(allocate.start_date.strftime("%d-%b-%y")) + '</td>'\
                                    '<td>' + str(allocate.end_date.strftime("%d-%b-%y")) + '</td>'\
                                '</tr>'
                released_count += 1
            message_body += '</table>' + '<br/>' + '<br/>'
            message_body += '<strong>List of team member who were assigned on the project:<strong> <br/>'
            message_body += '<table border="1" width="100%" cellpadding="0" bgcolor="#ededed">'
            message_body += '<tr style="text-align:center;">'\
                                '<th>' + 'Sr. No.' + '</th>'\
                                '<th>' + 'e-Zestian Name' + '</th>'\
                                '<th>' + 'Assigned From' + '</th>'\
                                '<th>' + 'Assigned To' + '</th>'\
                            '</tr>'
            total_count = 1
            for allocate_emp in rec.assignment_ids:
                message_body += '<tr style="text-align:center;">'\
                                    '<td>' + str(total_count) + '</td>'\
                                    '<td>' + str(allocate_emp.employee_id.name) + '</td>'\
                                    '<td>' + str(allocate_emp.start_date.strftime("%d-%b-%y")) + '</td>'\
                                    '<td>' + str(allocate_emp.end_date.strftime("%d-%b-%y")) + '</td>'\
                                '</tr>'
                total_count += 1
            message_body += '</table>' + '<br/>' + '<br/>'
            message_body += 'Note: Please ensure you are taking backup/deleting aa the project related code/document etc.\
                            to e-Zest repository to comply with required regulations. @QA Team Please take appropriate actions.\
                            <br/><br/>\
                            Thanks,\
                            <br/>\
                            Operations Team'
            email_to = rec.user_id.login if rec.user_id else 'unity@e-zest.in'
            email_cc = ['sysadmin@e-zest.in','qa-team@e-zest.in']
            for user in self.env['sale.operation.team'].search([('department_id', '=', rec.sale_order_id.sbu_id.id), ('company_id', '=', rec.company_id.id)]):
                email_cc.append(user.user_id.login)
                if user.email_text:
                    email_cc.append(user.email_text)
            if rec.department_id and rec.department_id.custom_manager_id:
                email_cc.append(rec.department_id.custom_manager_id.user_id.login)
            self.env['mail.mail'].create({
                'subject': 'Project Status- Closed - %s' % rec.name,
                'body_html': message_body,
                'email_from': 'unity@e-zest.in',
                'email_to': email_to,
                'email_cc': ', '.join(m for m in email_cc)
            }).sudo().send()

    def action_project_extend(self):
        view_id = self.env.ref('project_mgmt.extend_project_form').id
        return {
            'name': _('Extend Project'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'extend.project',
            'view_id': view_id,
            'target': 'new',
            'context': {
                        'default_actual_start_date': self.actual_start_date,
                        'default_planned_end_date': self.planned_end_date
                    }
        }

    def _cron_reminder_ryg(self):
        weekday = []
        if datetime.today().date().weekday() in [3, 4, 5, 6]:
            weekday.append(datetime.today().date())
        for rec in self.search([('state', '=', 'active'), ('ryg_review', '=', 'yes')]):
            if len(weekday) and not rec.ryg_id.filtered(lambda self: self.end_date >= weekday[-1]):
                template_id = self.env.ref('project_mgmt.send_ryg_remainder').id
                template = self.env['mail.template'].browse(template_id)
                template_values = {
                    'email_from': 'unity@e-zest.in',
                    'email_to': rec.user_id.login or False,
                    'email_cc': 'unity@e-zest.in',
                    'auto_delete': False,
                    'partner_to': False,
                    'scheduled_date': False,
                }
                template.sudo().write(template_values)
                with self.env.cr.savepoint():
                    template.with_context(lang=rec.user_id.lang).sudo().send_mail(rec.id, force_send=True, raise_exception=False)


class ProjectLocation(models.Model):
    _name = 'project.location'

    name = fields.Char(string='Name')


class ProjectTeamPlan(models.Model):
    _name = 'team.plan'

    team_plan_id = fields.Many2one('project.project', string='Project')
    role = fields.Char(string="Role")
    no_of_resources = fields.Char(string="Number of Resources")
    required_skills = fields.Char(string="Required Skills")


# class ProjectWhizibleCurrency(models.Model):
#     _name = 'project.whizible.currency'

#     name = fields.Char(string='Project Currency')


class ProjectWhiziblePractice(models.Model):
    _name = 'project.whizible.practice'
    _description = 'Project Whizible Practice'

    name = fields.Char(string='Practice')


class ProjectWhizibleOrganizationUnit(models.Model):
    _name = 'project.whizible.organization'
    _description = 'Project Whizible Organization'

    name = fields.Char(string='Delivery Unit')


class ProjectWhizibleStatus(models.Model):
    _name = 'project.whizible.status'
    _description = 'Project Whizible Status'

    name = fields.Char(string='Project Status')


class ProjectWhizibleLife(models.Model):
    _name = 'project.whizible.life'
    _description = 'Project Whizible Life'

    name = fields.Char(string='Life Cycle')


class ProjectSkillInherit(models.Model):
    _inherit = 'hr.employee.skill'

    project_id = fields.Many2one('project.project', string="Project")


class ProjectRYG(models.Model):
    _name = 'project.ryg'
    _description = 'Project Ryg'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _cron_ryg_form_close(self):
        record = self.search([])
        for rec in record:
            if rec.end_date == datetime.today().date():
                rec.state = "closed"

    name = fields.Char(string='RYG Assessment', tracking=True, default='RYG Assessment')
    project_id = fields.Many2one('project.project', string='Project', tracking=True)
    business_unit = fields.Many2one(string='Business Unit', related='project_id.department_id')
    ryg_status = fields.Selection([('red', 'RED'), ('yellow', 'YELLOW'), ('green', 'GREEN')], string='RYG status', default='green', tracking=True)
    remarks = fields.Text(string='Remarks', tracking=True)
    achievement = fields.Text(string='Achievements', tracking=True)
    ryg_status_change_date = fields.Date(string='Status Change Date', tracking=True, default=fields.Date.today())
    project_code = fields.Char(string='Project Code', related='project_id.name_seq')
    project_manager = fields.Many2one(string='Project Manager', related='project_id.user_id')
    start_date = fields.Date(string='Start Date', default=datetime.today().date() - timedelta(days=datetime.today().date().weekday()), tracking=True)
    end_date = fields.Date(string='End Date', default=datetime.today().date() - timedelta(days=datetime.today().date().weekday()) + (timedelta(days=6)), tracking=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    state = fields.Selection([
            ('open', 'Open'),
            ('closed', 'Closed'),
        ], string='Status', readonly=True, default='open', tracking=True)

    @api.model
    def create(self, vals):
        prev_start_date = self.search([('project_id', '=', vals.get('project_id'))]).mapped('start_date')
        if vals.get('start_date'):
            if datetime.strptime(vals.get('start_date'), "%Y-%m-%d").date() in prev_start_date:
                raise UserError(_("Duplicate Date RYG is not allowed"))
        return super(ProjectRYG, self).create(vals)

    def write(self, vals):
        start_date = datetime.today().date() - timedelta(days=datetime.today().date().weekday())
        end_date = datetime.today().date() - timedelta(days=datetime.today().date().weekday()) + (timedelta(days=6))
        if self.start_date < start_date and self.end_date < end_date:
            raise UserError(_("Edit previous week RYG is not allowed"))
        if vals.get('ryg_status'):
            self.ryg_status_change_date = datetime.today().date()
        return super(ProjectRYG, self).write(vals)

    def action_open_ryg(self):
        return {
            'name': 'RYG',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'project.ryg',
            'res_id': self.id,
            'target': 'current',
        }
