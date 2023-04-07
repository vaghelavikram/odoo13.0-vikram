# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime, timedelta, time
from pytz import timezone
from collections import OrderedDict
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo.osv.expression import get_unaccent_wrapper

class ProjectAssignment(models.Model):
    _name = 'project.assignment'
    _description = 'Project Assignment'
    _rec_name = 'project_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def action_create_allocation(self):
        view_form_id = self.env.ref('project_role.project_assignment_form').id
        action = {
            'type': 'ir.actions.act_window',
            'views': [(view_form_id, 'form')],
            'view_mode': 'form',
            'name': _('Allocation'),
            'res_model': 'project.assignment',
            'context': {'form_view_initial_mode': 'edit', 'default_employee_id': self.employee_id.id}
        }
        return action

    def action_open_allocation(self):
        view_form_id = self.env.ref('project_role.project_assignment_form').id
        action = {
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'views': [(view_form_id, 'form')],
            'view_mode': 'form',
            'name': _('Allocation'),
            'res_model': 'project.assignment',
            # 'context': {'form_view_initial_mode': 'edit', 'default_employee_id': self.employee_id.id}
        }
        return action

    def _get_project_actual_end_date(self):
        context = self._context
        project = self.env['project.project'].sudo().browse(context.get('default_project_id'))
        if project.actual_end_date:
            return project.actual_end_date.strftime('%Y-%m-%d')

    def _get_emp_task(self, project_id, start_date, end_date, employee_id):
        #get parent tasks of duration
        tasks = self.env['project.task'].sudo().search([('project_id', '=', project_id.id), ('task_type', '=', 'milestone'), ('user_id', '=', False)])
        related_task = []
        for task in tasks:
            if start_date and end_date:
                if (start_date.year == end_date.year):
                    if (start_date.month <= task.start_date.month and end_date.month >= task.date_deadline.month and start_date.year == task.start_date.year):
                        related_task.append(task)
                    elif (start_date.month >= task.start_date.month and end_date.month <= task.date_deadline.month and start_date.year == task.start_date.year):
                        related_task.append(task)
                else:
                    if (task.start_date.month >= start_date.month and start_date.year == task.start_date.year) or (start_date.year <= task.start_date.year and task.date_deadline.month <= end_date.month and task.date_deadline.year <= end_date.year):
                        related_task.append(task)
                    elif (task.start_date.month >= start_date.month and start_date.year == task.start_date.year) or (start_date.year <= task.start_date.year and task.date_deadline.month >= end_date.month and task.date_deadline.year < end_date.year):
                        related_task.append(task)
        # related_task = [task for task in tasks if (self.start_date.month <= task.start_date.month or self.start_date.year == task.start_date.year) and (self.end_date.month >= task.date_deadline.month or self.end_date.year >= task.date_deadline.year)]
        # task_list_month = [i.start_date.month for i in related_task if self.employee_id.name.lower() in i.name.lower()]
        task_list_ids = [i.id for i in related_task if employee_id.name.lower() in i.name.lower()]
        not_in_task_ids = []
        for t in related_task:
            if t.id not in task_list_ids:
                not_in_task_ids.append(t.id)
        return task_list_ids, not_in_task_ids

    @api.onchange('project_id', 'start_date', 'end_date')
    def _onchange_project(self):
        if self.end_date:
            if self.project_id and self.project_id.planned_end_date and self.end_date and (self.project_id.planned_end_date < self.end_date):
                if isinstance(self.id, int) and self.end_date:
                    self.end_date = False
                raise UserError(_("Assign till must be before to Project planned end date."))
        if self.employee_id and self.start_date and self.end_date:
            task_list_ids, not_in_task_ids = self._get_emp_task(self.project_id, self.start_date, self.end_date, self.employee_id)
            self.task_ids = [(6, 0, [i for i in task_list_ids])]
            self.parent_task_ids = [(6, 0, [n for n in not_in_task_ids])]
            if self.assign_status == 'confirmed':
                emp_tasks = self.env['project.task'].sudo().search([('project_id', '=', self.project_id.id), ('user_id', '=', self.employee_id.user_id.id)])
                emp_tasks = emp_tasks.mapped('date_deadline')
                not_in_task_ids = self.env['project.task'].sudo().browse(not_in_task_ids)
                not_in_task_ids = [i.id for i in not_in_task_ids if i.date_deadline not in emp_tasks]
                task_list_ids = self.env['project.task'].sudo().browse(task_list_ids)
                task_list_ids = [i.id for i in task_list_ids if i.date_deadline not in emp_tasks]
                self.parent_task_ids = [(6, 0, [n for n in not_in_task_ids])]
                self.task_ids = [(6, 0, [n for n in task_list_ids])]

    @api.onchange('employee_id')
    def _onchange_previous_allocation_filter(self):
        current_project_alloc = []
        prev_project_alloc = []
        if self.employee_id:
            project = self.env['project.project'].sudo().search([])
            project_assignment = self.sudo().search([('employee_id', '=', self.employee_id.id)])
            for assg in project_assignment:
                for i in project:
                    if assg.project_id.id == i.id:
                        if (assg.assign_status in ['confirmed'] or assg.allocation_completed is True) and assg.end_date and assg.end_date < datetime.today().date():
                            prev_project_alloc.append(assg.id)
                        elif (assg.assign_status in ['confirmed'] or assg.allocation_completed is True) and assg.end_date and assg.end_date > datetime.today().date():
                            current_project_alloc.append(assg.id)
            # [current_project_alloc.append(assg.id) for assg in project_assignment for i in project if assg.project_id.id == i.id]
            self.alloc_ids = [(6, 0, [c_alloc for c_alloc in current_project_alloc])]
            self.prev_alloc_ids = [(6, 0, [p_alloc for p_alloc in prev_project_alloc])]
            task_list_ids, not_in_task_ids = self._get_emp_task(self.project_id, self.start_date, self.end_date, self.employee_id)
            self.task_ids = [(6, 0, [i for i in task_list_ids])]
            self.parent_task_ids = [(6, 0, [n for n in not_in_task_ids])]
        else:
            self.alloc_ids = [(5, 0, 0)]
            self.prev_alloc_ids = [(5, 0, 0)]
            self.task_ids = False
            self.parent_task_ids = False

    # @api.onchange('start_date', 'end_date')
    # def _onchange_dates(self):
    #     if self.start_date:
    #         for employee in self.env['hr.employee'].search([]):
    #             allocate = 0
    #             if employee.project_assign_till and employee.project_assign_till < self.start_date:
    #                 employee.sudo().write({'allocate': 0})
    #             elif employee.project_assign_till and employee.project_assign_till > self.start_date:
    #                 alloc_before = self.search([('end_date', '<', self.start_date), ('employee_id','=',employee.id)])
    #                 alloc_bw = self.search([('end_date', '>=', self.start_date), ('employee_id', '=', employee.id)])
    #                 if alloc_before:
    #                     alloc_total = [i.allocation_percentage for i in alloc_before if i.assign_status == 'confirmed']
    #                     if alloc_total:
    #                         alloc_percent = employee.project_allocate - sum(alloc_total)
    #                         allocate = alloc_percent
    #                         employee.sudo().write({
    #                             'allocate': 100 - alloc_percent if alloc_percent != 100 else 100
    #                         })
    #                 if alloc_bw:
    #                     alloc_future_deallocate = alloc_bw.search([('assign_status', '=', 'deallocate'), ('end_date', '>', datetime.today().date()), ('employee_id', '=', employee.id)])
    #                     alloc_total = [i.allocation_percentage for i in alloc_bw if i.assign_status == 'confirmed' and self.end_date and i.start_date <= self.end_date]
    #                     if alloc_total:
    #                         if alloc_future_deallocate:
    #                             alloc_percent = sum(alloc_future_deallocate.mapped('allocation_percentage')) + sum(alloc_total)
    #                         else:
    #                             alloc_percent = sum(alloc_total)
    #                         allocate = alloc_percent
    #                         employee.sudo().write({
    #                             'allocate': 100 - alloc_percent if alloc_percent != 100 else 100
    #                         })
    #             else:
    #                 employee.sudo().write({'allocate': employee.project_allocate})
    #             employee.sudo().write({'project_allocate': allocate})

    @api.onchange('start_date', 'end_date', 'allocation_percentage', 'project_bill_status', 'assignment_filter', 'project_id')
    def _onchange_employee(self):
        res = {}
        if self.assign_status != 'confirmed':
            if self.env.context.get('default_employee_id'):
                self.employee_id = self.env.context.get('default_employee_id')
                self.is_error_message = False
            else:
                self.employee_id = False
                res['domain'] = {'employee_id': [('id', '=', False)]}
                # self.is_error_message = True
                self.is_error_message = False
        if self.start_date and self.end_date and self.project_id and not self.employee_id and self.assign_status not in ['confirmed','reject']:
            return self.search_employee_filter()
        return res

    @api.depends('start_date')
    def _compute_max_date(self):
        for rec in self:
            max_date = max([d.end_date for d in self.env['project.assignment'].sudo().search([('employee_id', '=', rec.employee_id.id)]) if d.end_date])
            if max_date == rec.end_date:
                rec.is_max_date = True
            else:
                rec.is_max_date = False

    @api.depends('start_date')
    def _get_operation_right(self):
        for rec in self:
            rec.is_operation_right = True
            if (rec.env.user.user_has_groups('project_mgmt.group_project_operations') or rec.env.user.user_has_groups('project_mgmt.group_project_operations_copy')) and rec.assign_status == 'confirmed':
                rec.is_operation_right = False
            elif not (rec.env.user.user_has_groups('project_mgmt.group_project_operations') or rec.env.user.user_has_groups('project_mgmt.group_project_operations_copy')) and rec.assign_status == 'confirmed':
                rec.is_operation_right = True
            elif rec.assign_status in ['planned','requested']:
                rec.is_operation_right = False

    @api.depends('employee_id')
    def _get_employee_detail(self):
        for rec in self:
            if rec.employee_id:
                rec.primary_skill = rec.employee_id.skills.name
                rec.resign_date = rec.employee_id.resign_date
                rec.exit_date = rec.employee_id.exit_date
                rec.sbu_id = rec.employee_id.sbu_id.id
                rec.sbu_id_custom = rec.employee_id.sbu_id.id
                rec.total_exp = rec.employee_id.total_exp
            else:
                rec.primary_skill = False
                rec.resign_date = False
                rec.exit_date = False
                rec.sbu_id = False
                rec.sbu_id_custom = False
                rec.total_exp = False

    def _search_max_date(self, operator, value):
        allocate_domain = []
        for i in self.env['project.assignment'].sudo().search([]):
            if operator == '=' and i.is_max_date == value:
                allocate_domain.append(('id','=', i.id))
            elif operator == '!=' and i.is_max_date != value:
                allocate_domain.append(('id','=', i.id))
            else:
                allocate_domain.append(('id','=', None))
        for rec in range(0,len(allocate_domain)-1):
            allocate_domain.insert(rec,'|')
        return allocate_domain

    def _search_skill(self, operator, value):
        skill_domain = []
        for i in self.env['project.assignment'].sudo().search([]):
            if i.primary_skill and operator == 'ilike' and (value in i.primary_skill.name if not isinstance(i.primary_skill, str) else value in i.primary_skill):
                skill_domain.append(('id','=', i.id))
            elif i.primary_skill and operator == 'not ilike' and (value not in i.primary_skill.name if not isinstance(i.primary_skill, str) else value not in i.primary_skill):
                skill_domain.append(('id','=', i.id))
            elif operator == '=' and (i.primary_skill.name == value if not isinstance(i.primary_skill, str) else i.primary_skill == value):
                skill_domain.append(('id','=', i.id))
            elif operator == '!=' and (i.primary_skill.name != value if not isinstance(i.primary_skill, str) else i.primary_skill != value):
                skill_domain.append(('id','=', i.id))
            else:
                skill_domain.append(('id','=', None))
        for rec in range(0,len(skill_domain)-1):
            skill_domain.insert(rec,'|')
        return skill_domain

    def _search_resign(self, operator, value):
        resign_domain = []
        value = datetime.strptime(value, '%Y-%m-%d').date()
        for i in self.env['project.assignment'].sudo().search([]):
            if i.resign_date and operator == '=' and i.resign_date == value:
                resign_domain.append(('id','=', i.id))
            elif i.resign_date and operator == '!=' and i.resign_date != value:
                resign_domain.append(('id','=', i.id))
            elif i.resign_date and operator == '>=' and i.resign_date >= value:
                resign_domain.append(('id','=', i.id))
            elif i.resign_date and operator == '<=' and i.resign_date <= value:
                resign_domain.append(('id','=', i.id))
            elif i.resign_date and operator == '>' and i.resign_date > value:
                resign_domain.append(('id','=', i.id))
            elif i.resign_date and operator == '<' and i.resign_date < value:
                resign_domain.append(('id','=', i.id))
            else:
                resign_domain.append(('id','=', None))
        for rec in range(0,len(resign_domain)-1):
            resign_domain.insert(rec,'|')
        return resign_domain

    def _search_exit(self, operator, value):
        exit_domain = []
        value = datetime.strptime(value, '%Y-%m-%d').date()
        for i in self.env['project.assignment'].sudo().search([]):
            if i.exit_date and operator == '=' and i.exit_date == value:
                exit_domain.append(('id','=', i.id))
            elif i.exit_date and operator == '!=' and i.exit_date != value:
                exit_domain.append(('id','=', i.id))
            elif i.exit_date and operator == '>=' and i.exit_date >= value:
                exit_domain.append(('id','=', i.id))
            elif i.exit_date and operator == '<=' and i.exit_date <= value:
                exit_domain.append(('id','=', i.id))
            elif i.exit_date and operator == '>' and i.exit_date > value:
                exit_domain.append(('id','=', i.id))
            elif i.exit_date and operator == '<' and i.exit_date < value:
                exit_domain.append(('id','=', i.id))
            else:
                exit_domain.append(('id','=', None))
        for rec in range(0,len(exit_domain)-1):
            exit_domain.insert(rec,'|')
        return exit_domain

    def _search_sbu(self, operator, value):
        sbu_domain = []
        for i in self.env['project.assignment'].sudo().search([]):
            if i.sbu_id and operator == 'ilike' and value in i.sbu_id.name:
                sbu_domain.append(('id','=', i.id))
            elif i.sbu_id and operator == 'not ilike' and value not in i.sbu_id.name:
                sbu_domain.append(('id','=', i.id))
            elif operator == '=' and i.sbu_id.name == value:
                sbu_domain.append(('id','=', i.id))
            elif operator == '!=' and i.sbu_id.name != value:
                sbu_domain.append(('id','=', i.id))
            else:
                sbu_domain.append(('id','=', None))
        for rec in range(0,len(sbu_domain)-1):
            sbu_domain.insert(rec,'|')
        return sbu_domain

    name = fields.Char(
        compute='_compute_name',
        store=True,
        index=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='project_id.company_id',
        store=True,
        readonly=True,
    )
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        required=True,
        tracking=True,
        default=lambda self: self.env.context.get('default_project_id'),
    )
    project_role_id = fields.Many2one(
        'hr.job',
        string='Assigned to Role',
        tracking=True,
    )
    role_ids = fields.Many2many(
        'hr.job',
        string='Role'
    )
    user_id = fields.Many2one(
        'res.users',
        string='e-Zestian User',
        tracking=True,
    )
    # project_billable_status = fields.Many2one(
    #     'project.billable.status',
    #     string='Billability Status',
    #     tracking=True,
    # )
    project_bill_status = fields.Selection([('25', '25% Billable'),
                                           ('50', '50% Billable'),
                                           ('100', '100% Billable'),
                                           ('0_unbilled', '0% UnBilled - Critical'),
                                           ('0_unbilled_buffer', '0% Unbilled Buffer'),
                                           ('0_unbilled_shadow', '0% Unbilled Shadow')], string='Billability Status',
                                           tracking=True, default='100')
    allocation_percentage = fields.Integer(
                string='Allocation(%)',
                tracking=True,
                default="100",
    )
    employee_id = fields.Many2one('hr.employee', string="e-Zestian", tracking=True)
    manager_id = fields.Many2one(related="project_id.user_id", string='Project Manager', tracking=True)
    start_date = fields.Date(
                string="Assigned From",
                tracking=True,
                default=datetime.today().date()
    )
    end_date = fields.Date(
                string="Assigned Till",
                readonly=False,
                tracking=True,
                default=_get_project_actual_end_date
    )
    project_assignment_skill_ids = fields.One2many('hr.employee.skill', 'assignment_id', string="Skills")
    assignment_filter = fields.Selection([('active', 'Allocation Available'),
                                          ('fully_billable', 'Billability Available'),
                                          ('all', 'All')], string='e-Zestian Filter', default="all")

    assign_status = fields.Selection([('planned', 'Planned'),
                                      ('requested', 'Requested'),
                                      ('confirmed', 'Approved'),
                                      ('reject', 'Rejected')], string='Assignment Status', default="planned", tracking=True,)
    alloc_ids = fields.One2many('project.assignment', 'previous_alloc_id')
    prev_alloc_ids = fields.One2many('project.assignment', 'prev_alloc_id')
    previous_alloc_id = fields.Many2one(
                         'project.assignment',
                         string='Current Allocations')
    prev_alloc_id = fields.Many2one(
                         'project.assignment',
                         string='Previous Allocations')
    alloc_state = fields.Selection([
                ('draft', 'Draft'),
                ('approval', 'Approve'),
            ], string='State', readonly=True, default='draft', tracking=True)
    change_manager = fields.Boolean(string="Change Manager?", tracking=True)
    is_operation_right = fields.Boolean(string='Has Operation Rights', compute="_get_operation_right")
    is_error_message = fields.Boolean(string='Error Message')
    filter_employee_ids = fields.Many2many('hr.employee')
    allocation_completed = fields.Boolean(string="Allocation Completed")
    is_search = fields.Boolean(string="Search")
    description_approve = fields.Text(string="Comment", tracking=True)
    allocation_tags = fields.Many2many('allocation.tag', string="Tag", tracking=True)
    bench_tags = fields.Many2many('allocation.bench.tag', string="Bench Tag", tracking=True)
    send_approve_mail = fields.Boolean(string="Send Mail?", default=True)
    send_release_mail = fields.Boolean(string="Send Release Mail?")
    team = fields.Many2one('allocation.team', string="Email to Team", default=lambda self: self.env['allocation.team'].sudo().search([('name', '=', 'Operations Team')]))
    change_dept = fields.Boolean(string="Change BU Head?")
    show_ryg = fields.Boolean(string="Show RYG?")
    is_max_date = fields.Boolean(compute="_compute_max_date", search="_search_max_date")
    primary_skill = fields.Char(string="Primary Skill", compute="_get_employee_detail", search="_search_skill")
    resign_date = fields.Date(string="Resign Date", compute="_get_employee_detail", search="_search_resign")
    exit_date = fields.Date(string="Exit Date", compute="_get_employee_detail", search="_search_exit")
    sbu_id = fields.Many2one('hr.department', string="SBU", compute="_get_employee_detail", search="_search_sbu")
    sbu_id_custom = fields.Many2one('hr.department', string="SBU Storable")
    total_exp = fields.Float(string="Total Exp", compute="_get_employee_detail")
    task_ids = fields.Many2many('project.task', string="Delivery Milestones")
    parent_task_ids = fields.Many2many('project.task', 'project_task_parent', 'parent_task', 'task')
    responsibility = fields.Text(string="Responsibility")
    # description_extend = fields.Text(string="Comment", tracking=True)
    last_update_date = fields.Date(string="Last Update Date Custom")
    project_efforts = fields.Float(string="Effective Project Efforts")
    is_unbilled_today = fields.Boolean(string="UnBilled Today")
    is_unallocated_today = fields.Boolean(string="Unallocated Today")


    # added cron job
    def _cron_calculate_unbilled_today(self):
        for rec in self.search([]):
            if rec.employee_id.total_billability == 0 and rec.employee_id.is_ezestian == True \
                    and rec.employee_id.active == True and rec.employee_id.account.name in ['Deployable - Billable',
                                                                                            'Temporarily - Deployable'] \
                    and rec.assign_status != 'reject' and rec.is_max_date == True:
                rec.is_unbilled_today = True
            else:
                rec.is_unbilled_today = False

    def _cron_calculate_unallocated_today(self):
        today = fields.Date.today()
        for rec in self.search([]):
            if rec.employee_id.project_assign_till:
                if rec.employee_id.project_allocate == 0 and rec.employee_id.is_ezestian == True and rec.employee_id.active == True \
                        and rec.is_max_date == True and rec.employee_id.account.name in ['Deployable - Billable',
                                                                                    'Temporarily - Deployable'] \
                        and rec.employee_id.project_assign_till < today \
                        and rec.assign_status != 'reject':
                    rec.is_unallocated_today = True
                else:
                    rec.is_unallocated_today = False

    def _cron_calculate_effective_efforts(self):
        for rec in self.search([]):
            admin = self.env['hr.employee'].search([('id', '=', 1)])
            tz = timezone(admin.resource_calendar_id.tz)
            today = fields.Date.today()
            month = rec.start_date.month
            year = rec.start_date.year
            person_month = []
            if rec.start_date.month == rec.end_date.month and rec.start_date.year == rec.end_date.year:
                date_from = tz.localize(datetime.combine(fields.Datetime.from_string(str(rec.start_date)), time.min))
                date_to = tz.localize(datetime.combine(fields.Datetime.from_string(str(rec.end_date)), time.min))
                if date_from == date_to and date_from.date().weekday() not in [5, 6]:
                    working_days = 1
                    effective_alloc_per_user = (rec.allocation_percentage * (working_days * 8)) / 100
                else:
                    working_days = admin.list_work_time_per_day(date_from, date_to, calendar=admin.resource_calendar_id)
                    effective_alloc_per_user = (rec.allocation_percentage * (len(working_days) * 8)) / 100
                person_month.append(effective_alloc_per_user)
            else:
                dates = OrderedDict(((rec.start_date + timedelta(_)).strftime(r"%m-%Y"), None) for _ in range((rec.end_date - rec.start_date).days)).keys()
                for d in dates:
                    d_split = d.split('-')
                    month, year = int(d_split[0]), int(d_split[1])
                    month_start = today + relativedelta(day=1, month=month, year=year)
                    month_end = today + relativedelta(day=31, month=month, year=year)
                    if rec.start_date > month_start:
                        date_start = rec.start_date - relativedelta(days=1)
                        date_from = tz.localize(datetime.combine(fields.Datetime.from_string(str(date_start)), time.min))
                    else:
                        date_from = tz.localize(datetime.combine(fields.Datetime.from_string(str(month_start)), time.min))
                    if rec.end_date < month_end:
                        date_end = rec.end_date + relativedelta(days=1)
                        date_to = tz.localize(datetime.combine(fields.Datetime.from_string(str(date_end)), time.min))
                    else:
                        date_to = tz.localize(datetime.combine(fields.Datetime.from_string(str(month_end)), time.min))
                    if date_from == date_to and date_from.date().weekday() not in [5, 6]:
                        working_days = 1
                        effective_alloc_per_user = (rec.allocation_percentage * (working_days * 8)) / 100
                    else:
                        working_days = admin.list_work_time_per_day(date_from, date_to, calendar=admin.resource_calendar_id)
                        effective_alloc_per_user = (rec.allocation_percentage * (len(working_days) * 8)) / 100
                    person_month.append(effective_alloc_per_user)
            rec.project_efforts = sum(person_month)
        
    def copy(self, default=None):
        self.ensure_one()
        if default is None:
            default = {}
        for rec in self:
            if rec.employee_id and rec.employee_id.project_assign_till:
                default['start_date'] = rec.employee_id.project_assign_till + timedelta(days=1)
                default['end_date'] = False
                default['assign_status'] = 'planned'
        res = super(ProjectAssignment, self).copy(default)
        return res

    def _compute_employee_allocation(self, start_date, end_date, employee_id=False):
        if employee_id:
            employees = self.env['hr.employee'].sudo().search([('id', '=', employee_id.id)])
        else:
            employees = self.env['hr.employee'].sudo().search([])
                # [('active', '=', True), ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable']),
                #  ('company_id', '=', self.company_id.id), ('joining_date', '!=', False), ('is_ezestian', '=', True)])
        for employee in employees:
            allocate = 0
            if employee.project_assign_till and employee.project_assign_till < start_date:
                employee.sudo().write({'allocate': 0})
            elif employee.project_assign_till and employee.project_assign_till > start_date:
                alloc_before = self.sudo().search([('end_date', '<', start_date), ('employee_id','=',employee.id)])
                alloc_bw = self.sudo().search([('end_date', '>=', start_date), ('employee_id', '=', employee.id)])
                if alloc_before:
                    alloc_total = [i.allocation_percentage for i in alloc_before if i.assign_status == 'confirmed']
                    if alloc_total:
                        alloc_percent = employee.project_allocate - sum(alloc_total)
                        allocate = alloc_percent
                        employee.sudo().write({
                            'allocate': 100 - alloc_percent if alloc_percent != 100 else 100
                        })
                if alloc_bw:
                    alloc_future_deallocate = alloc_bw.sudo().search([('allocation_completed', '=', True), ('end_date', '>', datetime.today().date()), ('employee_id', '=', employee.id)])
                    alloc_total = [i.allocation_percentage for i in alloc_bw if i.assign_status == 'confirmed' and end_date and i.start_date <= end_date]
                    if alloc_total:
                        if alloc_future_deallocate:
                            alloc_percent = sum(alloc_future_deallocate.mapped('allocation_percentage')) + sum(alloc_total)
                        else:
                            alloc_percent = sum(alloc_total)
                        allocate = alloc_percent
                        employee.sudo().write({
                            'allocate': 100 - alloc_percent if alloc_percent != 100 else 100
                        })
            else:
                employee.sudo().write({'allocate': employee.project_allocate})
            employee.sudo().write({'project_allocate': allocate})

    def _cron_employee_allocation(self):
        start_date = fields.date.today()
        # start_date = s_date - timedelta(days=7)
        end_date = fields.date.today()
        self._compute_employee_allocation(start_date, end_date)

    def _cron_allocation_complete(self):
        for rec in self.sudo().search([('assign_status', '=', 'confirmed')]):
            if rec.end_date < fields.Date.today():
                rec.allocation_completed = True
            if rec.end_date > fields.Date.today():
                rec.allocation_completed = False

    def _cron_allocate_task(self):
        today = fields.Date.today()
        for rec in self.sudo().search([('assign_status', '=', 'confirmed'), ('end_date', '>', today), ('allocation_completed', '=', False)]):
            tasks = self.env['project.task'].sudo().search([('project_id', '=', rec.project_id.id), ('task_type', '=', 'milestone'), ('user_id', '=', False)])
            for task in tasks:
                if task.sale_line_id.offering_type == 'tnm' and rec.employee_id.name.lower() in task.name.lower() and rec.start_date <= task.start_date and rec.end_date >= task.date_deadline:
                    task.user_id = rec.employee_id.user_id.id

    def _allocate_task(self, employee_id, project_id, start_date, end_date, parent_task_ids):
        for parent in parent_task_ids:
            task_start = False
            task_end = False
            if parent.start_date <= start_date and parent.date_deadline >= start_date:
                task_start = start_date
                task_end = parent.date_deadline
            if parent.start_date <= end_date and parent.date_deadline >= end_date:
                task_end = end_date
            if parent.start_date <= end_date and parent.date_deadline <= end_date:
                task_end = parent.date_deadline
            if parent.start_date >= start_date and parent.date_deadline >= start_date:
                task_start = parent.start_date
            if task_start and task_end:
                self.env['project.task'].sudo().create({
                    'name': 'Allocate: %s' % (parent.name),
                    'project_id': project_id.id,
                    'user_id': employee_id.user_id.id,
                    'task_type': 'activity',
                    'is_parent_task': True,
                    'start_date': task_start,
                    'date_deadline': task_end,
                    'parent_id': parent.id
                })

    def _get_department_manager(self, department_id):
        department = department_id
        email = []
        if department.custom_manager_id:
            email.append(department.custom_manager_id.user_id.login)
        if department.parent_id and 'Operations' in department.complete_name:
            while department.parent_id.name != 'Operations':
                department = department.parent_id
                if department.custom_manager_id:
                    email.append(department.custom_manager_id.user_id.login)
            if department.parent_id.name == 'Operations':
                if department.custom_manager_id:
                    email.append(department.custom_manager_id.user_id.login)
        return list(set(email))

    def action_approval(self):
        for rec in self:
            if not rec.employee_id:
                if not rec.description_approve:
                    raise UserError(_("You can't approve without e-Zestian"))
            if rec.project_id and rec.project_id.state == 'active':
                self._compute_employee_allocation(rec.start_date, rec.end_date, rec.employee_id)
                duplicate = self.sudo().search([('employee_id', '=', rec.employee_id.id), ('project_id','=',rec.project_id.id), ('end_date', '>=', rec.start_date), ('start_date', '<=', rec.end_date), ('assign_status', '=', 'confirmed')])
                if duplicate:
                    raise UserError(_("{0} already allocated".format(rec.employee_id.name)))
                if rec.employee_id.project_assign_till and rec.start_date <= rec.employee_id.project_assign_till and rec.employee_id.project_allocate + rec.allocation_percentage > 100:
                    raise UserError(_("{1} already allocated by {2}{0} till {3}".format('%',rec.employee_id.name, rec.employee_id.project_allocate, rec.employee_id.project_assign_till.strftime("%d-%b-%Y"))))
                if rec.employee_id and rec.change_manager:
                    allocations = self.sudo().search([('employee_id', '=', rec.employee_id.id)])
                    max_allocation = [(i.allocation_percentage, i) for i in allocations]
                    max_allocation.sort()
                    if max_allocation[-1][1].project_id.user_id:
                        if rec.employee_id.user_id != max_allocation[-1][1].project_id.user_id and rec.allocation_percentage > 0:
                            rec.employee_id.sudo().write({'parent_id': max_allocation[-1][1].project_id.user_id.employee_id.id})
                if rec.employee_id and rec.change_dept:
                    resp_hr = self.env['hr.employee.group'].sudo().search([('department_ids', '=', rec.project_id.department_id.id)])
                    rec.employee_id.sudo().write({
                        'department_id': rec.project_id.department_id.id,
                        'responsible_hr': resp_hr.id
                    })
                rec.assign_status = "confirmed"
                if rec.employee_id.total_billability == 0 and rec.employee_id.is_ezestian == True \
                        and rec.employee_id.active == True and rec.employee_id.account.name in ['Deployable - Billable',
                                                                                                'Temporarily - Deployable'] \
                        and rec.assign_status != 'reject' and rec.is_max_date == True:
                    rec.is_unbilled_today = True
                else:
                    rec.is_unbilled_today = False
                today = fields.Date.today()
                if rec.employee_id.project_assign_till:
                    if rec.employee_id.project_allocate == 0 and rec.employee_id.is_ezestian == True and rec.employee_id.active == True \
                            and rec.is_max_date == True and rec.employee_id.account.name in ['Deployable - Billable',
                                                                                             'Temporarily - Deployable'] \
                            and rec.employee_id.project_assign_till < today \
                            and rec.assign_status != 'reject':
                        rec.is_unallocated_today = True
                    else:
                        rec.is_unallocated_today = False
                rec.employee_id.sudo().write({'project_allocate': self.allocation_percentage})
                self.filtered(lambda hol: hol.assign_status == 'confirmed').activity_feedback(['project_role.mail_act_allocation_request'])
                self._allocate_task(rec.employee_id, rec.project_id, rec.start_date, rec.end_date, rec.task_ids)
                email_cc = False
                team = []
                if rec.team:
                    team = [user.login for t in rec.team for user in t.user_id]
                    team.append('hrd@e-zest.in,unity@e-zest.in')
                    if rec.project_id.user_id:
                        team.append(rec.project_id.user_id.login)
                emails = self._get_department_manager(rec.project_id.department_id)
                team.extend([i for i in emails])
                email_cc = ','.join(t for t in team)
                if rec.send_approve_mail:
                    template = self.env.ref('project_role.send_approved_allocation_email_user')
                    template_values = {
                        'email_from': 'unity@e-zest.in',
                        'email_to': rec.employee_id.user_id.login or False,
                        'email_cc': email_cc or 'hrd@e-zest.in,unity@e-zest.in,%s' % (rec.project_id.user_id.login),
                        'auto_delete': False,
                        'partner_to': False,
                        'scheduled_date': False,
                    }
                    template.sudo().write(template_values)
                    with self.env.cr.savepoint():
                        template.with_context(lang=self.env.user.lang).sudo().send_mail(rec.id, force_send=True, raise_exception=False)
            else:
                raise UserError(_("You can not approve allocation as it's project is not approved."))

    def action_deallocate(self):
        for rec in self:
            if rec.project_id.actual_end_date and rec.project_id.actual_end_date < fields.Date.today():
                rec.end_date = rec.project_id.actual_end_date
            else:
                rec.end_date = fields.Date.today()
            rec.assign_status = "deallocate"
            if rec.project_bill_status in ['0_unbilled', '0_unbilled_buffer', '0_unbilled_shadow']:
                project_bill_status = 0
            else:
                project_bill_status = rec.project_bill_status
            rec.employee_id.write({
                'project_allocate': rec.employee_id.project_allocate - rec.allocation_percentage,
                'total_billability': rec.employee_id.total_billability - int(project_bill_status),
                # 'allocate': int(rec.employee_id.allocate) - rec.allocation_percentage if int(rec.employee_id.allocate) > 0 else rec.employee_id.allocate
            })

    def action_requested(self):
        for rec in self:
            rec.assign_status = "requested"
            note = '<p>Dear Ops Team</p>\
                    <p>{0} request to allocate {1} on {2}.<p>\
                    <br/><br/>\
                    <p>Kindly click on \
                    <a href="/web#id={3}&amp;model={4}&amp;view_type=form"\
                    target="_blank" style="background-color: #875A7B; padding: 8px 16px 8px 16px;\
                    text-decoration: none; color: #fff; border-radius: 5px; font-size:13px;">View Allocation Request</a> for further process.</p>\
                    <br/><br/><br/>\
                    Thanks,\
                    <br/>\
                    Team Unity\
                    <p><br></p>'.format(rec.create_uid.name, rec.employee_id.name, rec.project_id.name, rec.id, rec._name)
            subject = 'Allocation Requested for %s' % (rec.employee_id.name)
            for alloc in self.filtered(lambda a: a.assign_status == 'requested'):
                for t in rec.team:
                    for user in t.user_id:
                        alloc.activity_schedule(
                            'project_role.mail_act_allocation_request',
                            user_id=user.id or self.env.user.id, note=note, summary=subject)

    def action_reject(self):
        for rec in self:
            rec.assign_status = "reject"
        activity = self.env['mail.activity'].sudo().search([('res_model', '=', 'project.assignment'), ('res_id', '=', self.id)])
        if activity:
            activity.unlink()

    @api.model
    def create(self, vals):
        if vals.get('employee_id'):
            employee = self.env['hr.employee'].sudo().search([('id', '=', vals.get('employee_id'))])
            start_date = str(vals.get('start_date'))
            deallocate = self.sudo().search([('employee_id','=',vals.get('employee_id')),('end_date','=',vals.get('start_date')), ('allocation_completed', '=', True)])
            duplicate = self.sudo().search([('employee_id', '=', vals.get('employee_id')), ('project_id','=',vals.get('project_id')), ('end_date', '>=', vals.get('start_date')), ('start_date', '<=', vals.get('end_date')), ('assign_status', '=', 'confirmed')])
            if duplicate:
                raise UserError(_("{0} already allocated".format(employee.name)))
            if not self.id and employee.project_assign_till and employee.project_allocate + vals.get('allocation_percentage') > 100 and start_date <= employee.project_assign_till.strftime('%Y-%m-%d'):
                raise UserError(_("You cannot allocate user more than 100{0}. {1} already allocated by {2}{0} till {3}".format('%',employee.name, employee.project_allocate, employee.project_assign_till.strftime("%d-%b-%Y"))))
            elif employee.project_assign_till and start_date <= employee.project_assign_till.strftime('%Y-%m-%d') and employee.project_allocate + vals.get('allocation_percentage') > 100:
                raise UserError(_("{1} already allocated by {2}{0} till {3}".format('%',employee.name, employee.project_allocate, employee.project_assign_till.strftime("%d-%b-%Y"))))
            elif deallocate and deallocate[0].allocation_percentage + vals.get('allocation_percentage') > 100:
                raise UserError(_("{1} already allocated till {2}".format('%',employee.name, deallocate[0].employee_id.project_assign_till.strftime("%d-%b-%Y"))))
        res = super(ProjectAssignment, self).create(vals)
        project = self.env['project.project'].sudo().browse(vals.get('project_id'))
        assign_end_date = datetime.strptime(vals.get('end_date'), '%Y-%m-%d').date() if vals.get('end_date') else False
        if project and project.planned_end_date and assign_end_date and (project.planned_end_date < assign_end_date):
            raise UserError(_("Assign till must be before to Project planned end date."))
        return res

    def write(self, vals):
        for rec in self:
            # for deallocation
            employee_id = rec.employee_id
            if isinstance(vals.get('end_date'), str):
                assign_end_date = datetime.strptime(vals.get('end_date'), '%Y-%m-%d').date()
            elif vals.get('end_date'):
                assign_end_date = vals.get('end_date')
            else:
                assign_end_date = rec.end_date
            if isinstance(vals.get('start_date'), str):
                assign_start_date = datetime.strptime(vals.get('start_date'), '%Y-%m-%d').date()
            elif vals.get('start_date'):
                assign_start_date = vals.get('start_date')
            else:
                assign_start_date = rec.start_date
            if len(vals):
                vals['last_update_date'] = fields.Date.today()
            if vals.get('allocation_tags'):
                tag = self.env['allocation.tag'].sudo().search([('name', '=', 'Released')])
                if not len(vals.get('allocation_tags')[0][2]):
                    raise UserError(_("Tag is required"))
                elif vals.get('allocation_tags')[0][2][0] == tag.id:
                    rec.allocation_completed = True
            if vals.get('end_date'):
                # if assign_end_date > datetime.today().date() and rec.assign_status == 'confirmed':
                #     raise UserError(_("You can't deallocate for future dates."))
                if rec.assign_status == 'confirmed' and rec.end_date > assign_end_date:
                    allocation_tag = len(vals.get('allocation_tags')[0][2]) if vals.get('allocation_tags') else rec.allocation_tags
                    if not allocation_tag and rec.end_date < datetime.today().date():
                        raise UserError(_("Tag is required"))
                    if rec.project_bill_status in ['0_unbilled', '0_unbilled_buffer', '0_unbilled_shadow']:
                        project_bill_status = 0
                    else:
                        project_bill_status = rec.project_bill_status
                    if assign_end_date < datetime.today().date():
                        rec.allocation_completed = True
                        employee_id.sudo().write({
                            'project_allocate': int(employee_id.project_allocate - rec.allocation_percentage),
                            'total_billability': int(employee_id.total_billability - int(project_bill_status))
                        })
                    emp_task = self.env['project.task'].sudo().search([('user_id', '=', rec.employee_id.user_id.id), ('project_id', '=', rec.project_id.id)])
                    for task in emp_task:
                        if task.date_deadline and task.date_deadline.month == assign_end_date.month and task.date_deadline.year == assign_end_date.year:
                            task.sudo().write({'date_deadline': assign_end_date})
                        if task.date_deadline and task.date_deadline.month > assign_end_date.month and task.date_deadline.year >= assign_end_date.year:
                            task.sudo().write({'sale_line_id': False, 'parent_id': False})
                            # task.unlink()
                    [t.unlink() for t in emp_task if t.parent_id.id is False and t.sale_line_id.id is False and t.task_type == 'activity']
                else:
                    if rec.assign_status == 'confirmed' and rec.end_date < assign_end_date:
                        emp_task = self.env['project.task'].sudo().search([('user_id', '=', rec.employee_id.user_id.id), ('project_id', '=', rec.project_id.id)])
                        allocate_task = []
                        for rec_task in emp_task:
                            if rec_task.start_date and rec_task.start_date <= rec.end_date:
                                if rec_task.parent_id:
                                    allocate_task.append(rec_task.parent_id.id)
                                else:
                                    allocate_task.append(rec_task.id)
                            if rec_task.date_deadline and rec_task.date_deadline.month == assign_end_date.month and rec_task.date_deadline.year == assign_end_date.year:
                                if rec_task.parent_id and rec_task.parent_id.date_deadline >= assign_end_date and rec_task.date_deadline < assign_end_date:
                                    rec_task.sudo().write({'date_deadline': assign_end_date})
                        task_ids = vals.get('task_ids')
                        if task_ids and task_ids[0][2] and len(task_ids[0]) >= 2 and len(task_ids[0][2]):
                            task_ids[0][2] = [i for i in task_ids[0][2] if i not in allocate_task]
                            parent_task = self.env['project.task'].sudo().search([('id', 'in', task_ids[0][2])])
                            self._allocate_task(rec.employee_id, rec.project_id, rec.start_date, assign_end_date, parent_task)
                        else:
                            task_list_ids, not_in_task_ids = self._get_emp_task(rec.project_id, rec.start_date, assign_end_date, rec.employee_id)
                            if self.assign_status == 'confirmed':
                                emp_tasks = self.env['project.task'].sudo().search([('project_id', '=', rec.project_id.id), ('user_id', '=', rec.employee_id.user_id.id)])
                                emp_tasks = emp_tasks.mapped('date_deadline')
                                task_list_ids = self.env['project.task'].sudo().browse(task_list_ids)
                                task_list_ids = [i.id for i in task_list_ids if i.date_deadline not in emp_tasks]
                                parent_task = self.env['project.task'].sudo().search([('id', 'in', task_list_ids)])
                                self._allocate_task(rec.employee_id, rec.project_id, rec.start_date, assign_end_date, parent_task)
                                self.task_ids = [(4, i.id) for i in parent_task]
                    rec.allocation_completed = False
            # end deallocation
            if vals.get('employee_id') and vals.get('allocation_percentage'):
                employee = self.env['hr.employee'].sudo().search([('id', '=', vals.get('employee_id'))])
                if employee.project_allocate - rec.allocation_percentage + vals['allocation_percentage'] > 100:
                    raise UserError(_("You cannot allocate user more than 100{0}. {1} already allocated by {2}{0}".format('%',employee.name, employee.project_allocate)))
            elif vals.get('allocation_percentage'):
                if int(rec.employee_id.allocate) - rec.allocation_percentage + vals['allocation_percentage'] > 100:
                    raise UserError(_("You cannot allocate user more than 100{0}. {1} already allocated by {2}{0}".format('%',rec.employee_id.name, rec.employee_id.project_allocate)))
            elif vals.get('employee_id'):
                employee = self.env['hr.employee'].sudo().search([('id', '=', vals.get('employee_id'))])
                start_date = str(rec.start_date)
                deallocate = self.sudo().search([('employee_id','=',vals.get('employee_id')),('end_date','=',assign_start_date), ('allocation_completed', '=', True)])
                duplicate = self.sudo().search([('employee_id', '=', vals.get('employee_id')), ('project_id','=',rec.project_id.id), ('end_date', '>=', assign_start_date), ('start_date', '<=', assign_end_date), ('assign_status', '=', 'confirmed')])
                # total_assign = self.search([('employee_id','=',vals.get('employee_id'),())])
                if duplicate:
                    raise UserError(_("{0} already allocated".format(employee.name)))
                if not rec.id and employee.project_assign_till and employee.project_allocate + rec.allocation_percentage > 100 and start_date <= employee.project_assign_till.strftime('%Y-%m-%d'):
                    raise UserError(_("You cannot allocate user more than 100{0}. {1} already allocated by {2}{0} till {3}".format('%',employee.name, employee.allocate, employee.project_assign_till.strftime("%d-%b-%Y"))))
                elif employee.project_assign_till and start_date <= employee.project_assign_till.strftime('%Y-%m-%d') and employee.project_allocate + rec.allocation_percentage > 100:
                    raise UserError(_("{1} already allocated by {2}{0} till {3}".format('%',employee.name, employee.project_allocate, employee.project_assign_till.strftime("%d-%b-%Y"))))
                elif deallocate and deallocate[0].allocation_percentage + rec.allocation_percentage > 100:
                    raise UserError(_("{1} already allocated till {2}".format('%',employee.name, deallocate[0].employee_id.project_assign_till.strftime("%d-%b-%Y"))))
                # elif employee.project_allocate + self.allocation_percentage > 100:
                #     raise UserError(_("{1} already allocated by {2}{0}".format('%',employee.name, employee.allocate)))
            elif vals.get('start_date'):
                employee = self.env['hr.employee'].sudo().search([('id', '=', rec.employee_id.id)])
                if vals.get('start_date') and employee.project_allocate + rec.allocation_percentage > 100 and assign_end_date < employee.project_assign_till:
                    raise UserError(_("You cannot allocate user more than 100{0}. {1} already allocated by {2}{0} till {3}".format('%', employee.name, employee.project_allocate, employee.project_assign_till.strftime("%d-%b-%Y"))))
        return super(ProjectAssignment, self).write(vals)

    def write_allocation(self):
        vals = {'end_date': self.end_date}
        self.sudo().write(vals)
        # return {'type': 'ir.actions.act_window_close'}

    def emp_allocate_task(self):
        parent_tasks = []
        for rec in self.task_ids:
            allocated_task = self.env['project.task'].sudo().search([('parent_id', '=', rec.id), ('user_id', '=', self.employee_id.user_id.id)])
            if not allocated_task:
                parent_tasks.append(rec)
        self._allocate_task(self.employee_id, self.project_id, self.start_date, self.end_date, parent_tasks)

    # @api.onchange('is_search')
    def search_employee_filter(self):
        if self.project_id and self.end_date:
            self.is_error_message = False
            res = {}
            if self.assignment_filter == 'all':  # show all free and allocate
                # employee_alloc.append(employee.id)
                employee_alloc = self.env['hr.employee'].sudo().search(
                    [('active', '=', True), ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable']),
                     ('company_id', '=', self.company_id.id), ('joining_date', '!=', False),
                     ('is_ezestian', '=', True)]).mapped('id')
                domain = {'employee_id': [('id', 'in', employee_alloc)]}
                res['domain'] = domain
                return res
            if self.start_date:
                self._compute_employee_allocation(self.start_date, self.end_date)
            if self.role_ids:
                employees = self.env['hr.employee'].sudo().search([('active', '=', True), ('job_id', 'in', self.role_ids.ids), ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable']), ('company_id', '=', self.company_id.id), ('joining_date', '!=', False)])
            elif self.project_id.is_internal:
                employees = self.env['hr.employee'].sudo().search([('active', '=', True), ('company_id', '=', self.company_id.id), ('joining_date', '!=', False)])
            elif self.role_ids and self.project_id.is_internal:
                employees = self.env['hr.employee'].sudo().search([('active', '=', True), ('job_id', 'in', self.role_ids.ids), ('company_id', '=', self.company_id.id), ('joining_date', '!=', False)])
            else:
                employees = self.env['hr.employee'].sudo().search([('active', '=', True), ('account', 'in', ['Deployable - Billable', 'Temporarily - Deployable']), ('company_id', '=', self.company_id.id), ('joining_date', '!=', False)])
            employee_alloc = []
            employees = employees.filtered(lambda emp: emp.company_id.id == self.project_id.company_id.id)
            for employee in employees:
                if self.assignment_filter == 'active':# exactly free
                    date_range = self.sudo().search([('employee_id', '=', employee.id), ('start_date', '<=', self.start_date),('end_date','<=',self.end_date)])
                    if (100 - employee.project_allocate) >= self.allocation_percentage:
                        employee_alloc.append(employee.id)
                    elif employee.project_assign_till and self.start_date and employee.project_assign_till < self.start_date:
                        employee_alloc.append(employee.id)
                    elif date_range:
                        total_alloc = sum([rec.allocation_percentage for rec in date_range])
                        if (100 - total_alloc) >= self.allocation_percentage:
                            employee_alloc.append(employee.id)
                elif self.assignment_filter == 'fully_billable':
                    if employee.total_billability < 100:
                        employee_alloc.append(employee.id)
                # elif self.assignment_filter == 'all':#show all free and allocate
                #     employee_alloc.append(employee.id)
                else:
                    employee_alloc.append(employee.id)
            # self.filter_employee_ids = employee_alloc
            domain = {'employee_id': [('id', 'in', employee_alloc)]}
            res['domain'] = domain
            return res

    def send_email_released_allocation(self):
        template = self.env.ref('project_role.email_template_allocation_released', raise_if_not_found=False)
        for rec in self:
            email_cc = False
            team = []
            if rec.team:
                team = [user.login for t in rec.team for user in t.user_id]
                team.append('qa-team@e-zest.in,unity@e-zest.in')
                if rec.project_id.user_id:
                    team.append(rec.project_id.user_id.login)
            emails = self._get_department_manager(rec.project_id.department_id)
            team.extend([i for i in emails])
            email_cc = ','.join(t for t in team)
            template_values = {
                'email_from': 'unity@e-zest.in',
                'email_to': rec.employee_id.user_id.login or False,
                'email_cc': email_cc or 'qa-team@e-zest.in,unity@e-zest.in,%s' % (rec.project_id.user_id.login),
                'auto_delete': False,
                'partner_to': False,
                'scheduled_date': False,
            }
            template.sudo().write(template_values)
            with self.env.cr.savepoint():
                template.with_context(lang=self.env.user.lang).sudo().send_mail(rec.id, force_send=True, raise_exception=False)
            rec.send_release_mail = True

    # @api.onchange('assignment_filter', 'allocation_percentage', 'start_date', 'project_bill_status')
    # def _onchange_assignment_filter(self):
    #     if self.project_id:
    #         if self.project_role_id:
    #             employees = self.env['hr.employee'].sudo().search([('active', '=', True), ('job_id', '=', self.project_role_id.id)])
    #         else:
    #             employees = self.env['hr.employee'].sudo().search([('active', '=', True)])
    #         employee_alloc = []
    #         res = {}
    #         for employee in employees:
    #             if self.assignment_filter == 'active':# exactly free
    #                 date_range = self.search([('employee_id', '=', employee.id), ('start_date', '<=', self.start_date),('end_date','<=',self.end_date)])
    #                 if (100 - employee.project_allocate) >= self.allocation_percentage:
    #                     employee_alloc.append(('id', '=', employee.id))
    #                 elif employee.project_assign_till and self.start_date and employee.project_assign_till < self.start_date:
    #                     employee_alloc.append(('id', '=', employee.id))
    #                 elif date_range:
    #                     total_alloc = sum([rec.allocation_percentage for rec in date_range])
    #                     if (100 - total_alloc) >= self.allocation_percentage:
    #                         employee_alloc.append(('id', '=', employee.id))
    #             elif self.assignment_filter == 'fully_billable':
    #                 if employee.total_billability < 100:
    #                     employee_alloc.append(('id', '=', employee.id))
    #             elif self.assignment_filter == 'all':#show all free and allocate
    #                 employee_alloc.append(('id', '=', employee.id))
    #             else:
    #                 employee_alloc.append(('id', '=', employee.id))
    #         for rec in range(0, len(employee_alloc)-1):
    #             employee_alloc.insert(rec, '|')
    #         domain = {'employee_id': employee_alloc if employee_alloc else [('id', '=', False)]}
    #         res['domain'] = domain
    #         return res

    @api.constrains('start_date', 'end_date')
    def _check_allocation_end_date(self):
        for rec in self:
            if rec.project_id and rec.project_id.planned_end_date and rec.start_date and (rec.project_id.planned_end_date < rec.start_date):
                raise UserError(_("Assign from must be before Project planned end date."))
            if rec.project_id and rec.project_id.actual_start_date and rec.end_date and (rec.project_id.actual_start_date > rec.end_date):
                raise UserError(_("Assign till date must be after Project actual start date."))
            if rec.project_id and rec.project_id.actual_start_date and rec.start_date and (rec.project_id.actual_start_date > rec.start_date):
                raise UserError(_("Project actual start date must be greater than Assign from date."))
            if rec.start_date and rec.end_date and rec.start_date > rec.end_date:
                raise UserError(_("Assign till must be greater than Assign from."))

    # _sql_constraints = [
    #     (
    #         'project_role_user_uniq',
    #         'unique (project_id, role_id, user_id)',
    #         'User may be assigned per role only once within a project!'
    #     ),
    # ]

    # @api.depends('project_id.name', 'role_id.name', 'user_id.name')
    # def _compute_name(self):
    #     for assignment in self:
    #         assignment.name = _('%s as %s on %s') % (
    #             assignment.user_id.name,
    #             assignment.role_id.name,
    #             assignment.project_id.name,
    #         )

    # @api.multi
    # @api.constrains('role_id', 'user_id')
    # def _check_assignable(self):
    #     for assignment in self:
    #         if not assignment.role_id.can_assign(assignment.user_id):
    #             raise ValidationError(_(
    #                 'User %s can not be assigned to role %s.'
    #             ) % (
    #                 assignment.user_id.name,
    #                 assignment.role_id.name,
    #             ))


class ProjectSkillInherit(models.Model):
    _inherit = 'hr.employee.skill'

    assignment_id = fields.Many2one('project.assignment', string="Project")


class AllocationTag(models.Model):
    _name = 'allocation.tag'
    _description = 'Allocation Tag'

    name = fields.Char(string="Tag Name")

class AllocationBenchTag(models.Model):
    _name = 'allocation.bench.tag'
    _description = 'Allocation Bench Tag'

    name = fields.Char(string="Tag Name")

class AllocationTeam(models.Model):
    _name = 'allocation.team'
    _description = 'Allocation Team'

    name = fields.Char(string="Team Name")
    user_id = fields.Many2many('res.users', string="Team Member")
