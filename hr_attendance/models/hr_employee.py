# -*- coding: utf-8 -*-
# Part of Unity. See LICENSE file for full copyright and licensing details.

import pytz
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, exceptions, _, SUPERUSER_ID


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    attendance_ids = fields.One2many('hr.attendance', 'employee_id', help='list of attendances for the e-Zestian')
    last_attendance_id = fields.Many2one('hr.attendance', compute='_compute_last_attendance_id', store=True)
    last_check_in = fields.Datetime(related='last_attendance_id.check_in', store=True)
    last_check_out = fields.Datetime(related='last_attendance_id.check_out', store=True)
    attendance_state = fields.Selection(string="Attendance Status", compute='_compute_attendance_state', selection=[('checked_out', "Checked out"), ('checked_in', "Checked in")])
    hours_last_month = fields.Float(compute='_compute_hours_last_month')
    hours_today = fields.Float(compute='_compute_hours_today')
    hours_last_month_display = fields.Char(compute='_compute_hours_last_month')

    def _compute_presence_state(self):
        """
        Override to include checkin/checkout in the presence state
        Attendance has the second highest priority after login
        """
        super()._compute_presence_state()
        employees = self.filtered(lambda employee: employee.hr_presence_state != 'present')
        for employee in employees:
            if employee.attendance_state == 'checked_out' and employee.hr_presence_state == 'to_define':
                employee.hr_presence_state = 'absent'
        for employee in employees:
            if employee.attendance_state == 'checked_in':
                employee.hr_presence_state = 'present'

    def _compute_hours_last_month(self):
        for employee in self:
            now = datetime.now()
            start = now + relativedelta(months=-1, day=1, hour=00, minute=00)
            end = now + relativedelta(days=-1, day=1, hour=23, minute=59)
            attendances = self.env['hr.attendance'].search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', start),
                ('check_out', '<=', end),
            ])
            employee.hours_last_month = round(sum(attendances.mapped('worked_hours')), 2)
            employee.hours_last_month_display = "%g" % round(employee.hours_last_month, 2)

    def _compute_hours_today(self):
        now = fields.Datetime.now()
        now_utc = pytz.utc.localize(now)
        for employee in self:
            # start of day in the employee's timezone might be the previous day in utc
            tz = pytz.timezone(employee.tz)
            now_tz = now_utc.astimezone(tz)
            start_tz = now_tz + relativedelta(hour=0, minute=0)  # day start in the employee's timezone
            start_naive = start_tz.astimezone(pytz.utc).replace(tzinfo=None)

            attendances = self.env['hr.attendance'].search([
                ('employee_id', '=', employee.id),
                ('check_in', '<=', now),
                '|', ('check_out', '>=', start_naive), ('check_out', '=', False),
            ])

            worked_hours = 0
            for attendance in attendances:
                delta = (attendance.check_out or now) - max(attendance.check_in, start_naive)
                worked_hours += delta.total_seconds() / 3600.0
            employee.hours_today = worked_hours

    @api.depends('attendance_ids')
    def _compute_last_attendance_id(self):
        for employee in self:
            employee.last_attendance_id = self.env['hr.attendance'].search([
                ('employee_id', '=', employee.id),
            ], limit=1)

    @api.depends('last_attendance_id.check_in', 'last_attendance_id.check_out', 'last_attendance_id')
    def _compute_attendance_state(self):
        for employee in self:
            att = employee.last_attendance_id.sudo()
            employee.attendance_state = att and not att.check_out and 'checked_in' or 'checked_out'

    @api.model
    def attendance_scan(self, barcode):
        """ Receive a barcode scanned from the Kiosk Mode and change the attendances of corresponding employee.
            Returns either an action or a warning.
        """
        employee = self.sudo().search([('barcode', '=', barcode)], limit=1)
        if employee:
            return employee._attendance_action('hr_attendance.hr_attendance_action_kiosk_mode')
        return {'warning': _('No e-Zestian corresponding to barcode %(barcode)s') % {'barcode': barcode}}

    def attendance_manual(self, next_action, entered_pin=None):
        self.ensure_one()
        can_check_without_pin = not self.env.user.has_group('hr_attendance.group_hr_attendance_use_pin') or (self.user_id == self.env.user and entered_pin is None)
        if can_check_without_pin or entered_pin is not None and entered_pin == self.sudo().pin:
            return self._attendance_action(next_action)
        return {'warning': _('Wrong PIN')}

    def _attendance_action(self, next_action):
        """ Changes the attendance of the employee.
            Returns an action to the check in/out message,
            next_action defines which menu the check in/out message should return to. ("My Attendances" or "Kiosk Mode")
        """
        self.ensure_one()
        employee = self.sudo()
        action_message = self.env.ref('hr_attendance.hr_attendance_action_greeting_message').read()[0]
        action_message['previous_attendance_change_date'] = employee.last_attendance_id and (employee.last_attendance_id.check_out or employee.last_attendance_id.check_in) or False
        action_message['employee_name'] = employee.name
        action_message['barcode'] = employee.barcode
        action_message['next_action'] = next_action
        action_message['hours_today'] = employee.hours_today

        if employee.user_id:
            modified_attendance = employee.with_user(employee.user_id)._attendance_action_change()
        else:
            modified_attendance = employee._attendance_action_change()
        action_message['attendance'] = modified_attendance.read()[0]
        return {'action': action_message}

    def _attendance_action_change(self):
        """ Check In/Check Out action
            Check In: create a new attendance record
            Check Out: modify check_out field of appropriate attendance record
        """
        self.ensure_one()
        action_date = fields.Datetime.now()

        if self.attendance_state != 'checked_in':
            vals = {
                'employee_id': self.id,
                'check_in': action_date,
            }
            return self.env['hr.attendance'].create(vals)
        attendance = self.env['hr.attendance'].search([('employee_id', '=', self.id), ('check_out', '=', False)], limit=1)
        if attendance:
            attendance.check_out = action_date
        else:
            raise exceptions.UserError(_('Cannot perform check out on %(empl_name)s, could not find corresponding check in. '
                'Your attendances have probably been modified manually by human resources.') % {'empl_name': self.sudo().name, })
        return attendance

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if 'pin' in groupby or 'pin' in self.env.context.get('group_by', '') or self.env.context.get('no_group_by'):
            raise exceptions.UserError(_('Such grouping is not allowed.'))
        return super(HrEmployeeBase, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)