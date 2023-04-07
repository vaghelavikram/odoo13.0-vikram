# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from odoo import models, fields, api, exceptions, _, SUPERUSER_ID


class HrEmployeeBaseInherit(models.AbstractModel):
    _inherit = "hr.employee.base"

    def _attendance_action_change(self):
        """ Check In/Check Out action
            Check In: create a new attendance record
            Check Out: modify check_out field of appropriate attendance record
        """

        self.ensure_one()
        action_date = fields.Datetime.now()
        check_attendance = self.env['hr.attendance'].search([('employee_id', '=', self.id)])
        check_attendance = [i for i in check_attendance if i.check_in.date() == action_date.date()]
        if check_attendance:
            raise exceptions.UserError(_('Already check_in for %(date)s date.') % {'date': action_date.date(), })
        if self.attendance_state != 'checked_in':
            vals = {
                'employee_id': self.id,
                'check_in': action_date,
                'check_out': action_date + timedelta(hours=8)
            }
            return self.env['hr.attendance'].create(vals)
        attendance = self.env['hr.attendance'].search([('employee_id', '=', self.id), ('check_in', '=', action_date)], limit=1)
        if attendance:
            attendance.check_out = action_date + timedelta(hours=8)
        else:
            raise exceptions.UserError(_('Cannot perform check out on %(empl_name)s, could not find corresponding check in. '
                'Your attendances have probably been modified manually by human resources.') % {'empl_name': self.sudo().name, })
        return attendance
