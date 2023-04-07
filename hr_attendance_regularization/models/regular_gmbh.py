# -*- coding: utf-8 -*-
from odoo import fields, api, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, time
from dateutil.relativedelta import relativedelta
import pytz


class Regularization(models.Model):
    _name = 'hr.attendance.regular'
    _rec_name = 'employee_id'
    _description = 'Attendance Approval Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.depends('from_date', 'to_date')
    def _get_compute_worked_hours(self):
        for attendance in self:
            if attendance.from_date and attendance.to_date:
                if attendance.divide_date:
                    worked_hours = ((attendance.from_date - attendance.to_date).total_seconds() / 3600.0) * ((attendance.from_date - attendance.to_date).days)
                    attendance.worked_hours = worked_hours
                elif attendance.is_full_day:
                    check_in = datetime.combine(attendance.from_date.date(), time.min)
                    check_out = datetime.combine(attendance.to_date.date(), time.max)
                    attendance.worked_hours = (check_out - check_in).total_seconds() / 3600.0
                else:
                    attendance.worked_hours = (attendance.to_date - attendance.from_date).total_seconds() / 3600.0

    @api.onchange('is_full_day')
    def _onchange_full_day(self):
        if self.is_full_day:
            self.to_date = self.from_date + relativedelta(days=7)

    reg_category = fields.Many2one('hr.reg.categories', string='Category', required=True)
    from_date = fields.Datetime(string='From Date', required=True, default=(datetime.today().replace(hour=3, minute=30, second=00)))
    to_date = fields.Datetime(string='To Date', required=True, default=(datetime.today().replace(hour=12, minute=30, second=00)))
    reg_reason = fields.Text(string='Details', required=True)
    employee_id = fields.Many2one('hr.employee', string="e-Zestian", default=lambda self: self.env.user.employee_id, required=True)
    identification_id = fields.Char(related="employee_id.identification_id")
    worked_hours = fields.Float(string='Total Worked hours', compute="_get_compute_worked_hours")
    manager_id = fields.Many2one(related="employee_id.parent_id", string='Manager', track_visibility='onchange')
    # attendance_regular_ids = fields.Many2many('hr.regular.line', string="Attendace Ids", compute="_compute_regular_attendance")
    divide_date = fields.Boolean(string="Mark for Working Days", default=True)
    company_id = fields.Many2one('res.company', 'Company', copy=False, readonly=True,
                                 default=lambda self: self.env.user.company_id)
    skip_dates = fields.Text(string="Skip Dates")
    is_full_day = fields.Boolean(string="Worked 24/7")
    state = fields.Selection([
        ('submit', 'Approved'),
        ('reject', 'Rejected')], default='submit', track_visibility='onchange', string='State')

    @api.model
    def create(self, vals):
        # from_date = datetime.strptime(vals.get('from_date'), "%Y-%m-%d %H:%M:%S")
        # to_date = datetime.strptime(vals.get('to_date'), "%Y-%m-%d %H:%M:%S")
        user_tz = pytz.timezone(self._context.get('tz') or self.env.user.tz)
        from_date = pytz.utc.localize(datetime.strptime(vals.get('from_date'), "%Y-%m-%d %H:%M:%S")).astimezone(user_tz).replace(tzinfo=None)
        to_date = pytz.utc.localize(datetime.strptime(vals.get('to_date'), "%Y-%m-%d %H:%M:%S")).astimezone(user_tz).replace(tzinfo=None)
        attendance = self.env['hr.attendance'].search([
            ('employee_id', '=', vals.get('employee_id')),
            ('check_in', '>=', from_date),
            ('check_out', '<=', to_date)
        ])
        if attendance:
            raise UserError(_("You have already regularize for this date"))
        leave, hdl = self.env['attendance.regular']._check_leave_date(vals.get('employee_id'))
        [leave.remove(dl['date']) for dl in hdl if dl['date'] in leave]
        skip_dates = [str(from_date) for i in leave if i == from_date]
        skip_dates.extend([str(to_date) for i in leave if i == to_date])
        employee = self.env['hr.employee'].search([('id', '=', vals.get('employee_id'))])
        category = self.env['hr.reg.categories'].search([('id', '=', vals.get('reg_category'))])
        if to_date.date() < from_date.date():
            raise ValidationError(_('Choose the date correctly. Worked hours should greater than 0'))
        if (from_date not in leave) and not attendance and not vals.get('divide_date'):
            if vals.get('is_full_day'):
                self.env['hr.attendance'].sudo().create({
                    'check_in': datetime.combine(from_date.date(), time.min),
                    'check_out': datetime.combine(to_date.date(), time.max),
                    'employee_id': vals.get('employee_id'),
                    'company_id': employee.company_id.id,
                    'manager_id': employee.parent_id.id,
                    'source_check_in': category.name + ' IN',
                    'source_check_out': category.name + ' OUT',
                    'regular_id': vals.get('id')
                })
            else:
                self.env['hr.attendance'].sudo().create({
                    'check_in': from_date,
                    'check_out': to_date,
                    'employee_id': vals.get('employee_id'),
                    'company_id': employee.company_id.id,
                    'manager_id': employee.parent_id.id,
                    'source_check_in': category.name + ' IN',
                    'source_check_out': category.name + ' OUT',
                    'regular_id': vals.get('id')
                })
        date_list = []
        if vals.get('divide_date') and not attendance:
            check_in = from_date
            if not to_date.date() == from_date.date():
                for x in range(0, int((to_date.date() - from_date.date()).days)):
                    date_list.append(check_in)
                    check_in = check_in + relativedelta(days=1)
                date_list.append(to_date)
                for rec in date_list:
                    if rec.date() in leave:
                        skip_dates.append(rec.date())
                    if rec.date() not in leave and not vals.get('is_full_day'):
                        self.env['hr.attendance'].sudo().create({
                            'check_in': rec,
                            'check_out': datetime.combine(rec, to_date.time()),
                            'employee_id': vals.get('employee_id'),
                            'company_id': employee.company_id.id,
                            'manager_id': employee.parent_id.id,
                            'source_check_in': category.name + ' IN',
                            'source_check_out': category.name + ' OUT',
                            'regular_id': vals.get('id')
                        })
                    elif rec.date() not in leave and vals.get('is_full_day'):
                        self.env['hr.attendance'].sudo().create({
                            'check_in': datetime.combine(rec.date(), time.min),
                            'check_out': datetime.combine(rec.date(), time.max),
                            'employee_id': vals.get('employee_id'),
                            'company_id': employee.company_id.id,
                            'manager_id': employee.parent_id.id,
                            'source_check_in': category.name + ' IN',
                            'source_check_out': category.name + ' OUT',
                            'regular_id': vals.get('id')
                        })
            elif from_date not in leave and to_date.date() == from_date.date():
                if vals.get('is_full_day'):
                    self.env['hr.attendance'].sudo().create({
                        'check_in': datetime.combine(from_date.date(), time.min),
                        'check_out': datetime.combine(to_date.date(), time.max),
                        'employee_id': vals.get('employee_id'),
                        'company_id': employee.company_id.id,
                        'manager_id': employee.parent_id.id,
                        'source_check_in': category.name + ' IN',
                        'source_check_out': category.name + ' OUT',
                        'regular_id': vals.get('id')
                    })
                else:
                    self.env['hr.attendance'].sudo().create({
                        'check_in': from_date,
                        'check_out': to_date,
                        'employee_id': vals.get('employee_id'),
                        'company_id': employee.company_id.id,
                        'manager_id': employee.parent_id.id,
                        'source_check_in': category.name + ' IN',
                        'source_check_out': category.name + ' OUT',
                        'regular_id': vals.get('id')
                    })
        if skip_dates:
            vals['skip_dates'] = list(set([d.strftime('%a, %d-%b-%Y') for d in skip_dates]))
        else:
            vals['skip_dates'] = False
        return super(Regularization, self).create(vals)

    def regular_rejection(self):
        self.write({
            'state': 'reject'
        })
        date_list = []
        from_date = self.from_date
        for x in range(0, int((self.to_date.date() - self.from_date.date()).days)):
            date_list.append(from_date.date())
            from_date = from_date + relativedelta(days=1)
        date_list.append(self.to_date.date())
        attendance = self.env['hr.attendance'].search([('employee_id', '=', self.employee_id.id)])
        for atten in attendance:
            if atten.check_in.date() in date_list:
                self._cr.execute("DELETE FROM hr_attendance WHERE id={0}".format(atten.id))

class RegCategory(models.Model):

    _name = 'hr.reg.categories'
    _description = 'Regularization Categories'
    _rec_name = 'name'

    name = fields.Char(string='Category')
