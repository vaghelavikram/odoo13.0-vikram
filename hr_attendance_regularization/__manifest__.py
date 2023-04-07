# -*- coding: utf-8 -*-

{
    'name': "Banas Tech Attendance Regularization",
    'version': '13.0',
    'summary': """Assigning Attendance for the Employees with Onsight Jobs""",
    'description': """Assigning Attendance for the Employees with Onsight Jobs through the requests by Employees """,
    'category': 'Human Resources',
    'author': 'Banas Tech PVT Ltd.',
    'company': 'Banas Tech PVT Ltd .',
    'depends': ['base', 'hr', 'contacts'],
    'data': [
            'security/ir.model.access.csv',
            # 'security/security.xml',
            # 'data/attendance_approval_email_template.xml',
            # 'views/category.xml',
            # 'views/regularization_views.xml',
            # 'views/regular_gmbh_views.xml',
            # 'views/assets.xml',
            # 'wizard/confirm_regularize_wizard.xml',
            ],
    'demo': [],
    'qweb': ['static/src/xml/tree_inherit.xml'],
    'images': ['static/description/icon.png'],
    'license': "AGPL-3",
    'installable': True,
    'application': True,
}
