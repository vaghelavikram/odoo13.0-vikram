# -*- coding: utf-8 -*-
{
    'name': "Greeting",
    'summary': "Generate Birthday/Anniversary Greeting",
    'description': """Generate Birthday/Anniversary Greeting""",
    'version': '0.1',
    'author': 'Banas PVT Ltd.',
    'company': 'Banas PVT Ltd.',
    'license': 'LGPL-3',
    'depends': ['base', 'hr', 'hr_employee_updation'],
    'data': [
            'security/ir.model.access.csv',
            'views/birthday_temp.xml',
            'views/anniversary_temp.xml',
            'views/cron_greeting.xml',
    ],
    'qweb': [],
    'installable': True,
    "external_dependencies": {
        'python37': ['numpy']
    },
}
