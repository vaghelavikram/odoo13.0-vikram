# -*- coding: utf-8 -*-

{
    'name': 'Banas Tech Hr Employee Documents',
    'version': '13.0',
    'summary': """Manages Employee Documents With Expiry Notifications.""",
    'description': """Manages Employee Related Documents with Expiry Notifications.""",
    'author': 'Banas Tech PVT Ltd.',
    'company': 'Banas Tech PVT Ltd.',
    'depends': ['base', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        # 'views/assets.xml',
        # 'views/employee_document_view.xml',
    ],
    'images': ['static/description/icon.png'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
