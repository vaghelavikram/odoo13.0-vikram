# -*- coding: utf-8 -*-
{
    'name': 'Banas Tech Employee Attendance',
    'version': '13.0',
    'summary': """Attendance Integration with MSSQL using PYODBC""",
    'description': 'This module helps you to add employee attendance records \
                   which is fetch from MSSQL using SP.',
    'author': 'Banas Tech PVT Ltd.',
    'company': 'Banas Tech PVT Ltd.',
    'depends': ['base', 'hr_employee_updation', 'hr_attendance', 'hr_attendance_regularization', 'report_xlsx'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/hr_employee_attendance.xml',
        'report/report_attendance.xml',
        'report/report_attendance_wizard.xml',
        'report/report_employee_attendance.xml',
        'views/assets.xml',
        'views/res_config_setting_views.xml',
    ],
    'demo': [],
    'qweb': [
        "static/src/xml/employee_summary.xml",
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
