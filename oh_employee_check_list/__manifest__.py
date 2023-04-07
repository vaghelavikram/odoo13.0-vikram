# -*- coding: utf-8 -*-

{
    'name': 'Banas Tech Hr Employee Checklist',
    'version': '13.0',
    'summary': """Manages Employee's Entry & Exit Process""",
    'description': """This module is used to remembering the employee's entry and exit progress.""",
    'author': 'Banas Tech PVT Ltd.',
    'company': 'Banas Tech PVT Ltd.',
    'depends': ['base', 'oh_employee_documents_expiry', 'project_role'],
    'data': [
        'security/ir.model.access.csv',
        # 'data/data.xml',
        'views/employee_form_inherit_view.xml',
        'views/checklist_view.xml',
        'views/employee_check_list_view.xml',
        'views/settings_view.xml',
        'views/document_file_type_view.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}

