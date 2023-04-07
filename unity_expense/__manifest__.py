# -*- coding: utf-8 -*-
{
    'name': 'Banas Tech Expense',
    'version': '13.0',
    'summary': """Adding Advanced Fields res.user for e-Zestian and non e-Zestian""",
    'description': 'This module helps you to add user as an e-Zestian \
                    and non e-Zestian and based on that they can see \
                    the infomation and edit it.',
    'author': 'Banas Tech PVT Ltd.',
    'company': 'Banas Tech PVT Ltd.',
    'depends': [
        'base',
        'hr_expense'
    ],
    'data': [
        'security/ir.model.access.csv',
        # 'security/security.xml',
        # 'data/unity_expense_data.xml',
        # 'views/report_expense_inherit.xml',
        # 'views/report_planned_expense.xml',
        # 'views/hr_expense_inherit_view.xml',
        # 'views/hr_planned_expense_view.xml',
        # 'views/res_config_settings_view.xml',
    ],
    'demo': [],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
