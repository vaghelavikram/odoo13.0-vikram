# -*- coding: utf-8 -*-

{
    'name': 'Hr Employee Info',
    'version': '0.1',
    'summary': """Adding Advanced Fields In Employee Master""",
    'description': 'This module helps you to add more information in employee records.',
    'author': 'Banas Tech PVT Ltd.',
    'company': 'Banas Tech PVT Ltd.',
    'depends': ['base', 'mail', 'hr_org_chart', 'oh_employee_check_list', 'report_xlsx', 'hr_gamification', 'unity_expense'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/assets.xml',
        'data/confirmation_period_template.xml',
        'data/fnf_email_template.xml',
        'report/report_leave.xml',
        'views/hr_employee_view.xml',
        'views/hr_notification.xml',
        'views/hr_contract_type.xml',
        'views/hr_job_inherit.xml',
        'views/hr_unit.xml',
        'views/probation_survey_form.xml',
        'views/res_config_setting_views.xml',
        'views/relieving_letter.xml',
        'views/confirmation_letter.xml',
        'views/experience_letter.xml',
        'views/address_proof_letter.xml',
        'views/employee_resume_format.xml',
        'views/employee_certificate.xml',
        'views/hr_nda_report.xml',
        'views/hr_coc_report.xml',
        'views/hr_contractor_nda_report.xml',
        'views/austria_agreement_letter.xml',
        'views/antisexual_policy.xml',
        'views/intern_agreement_letter.xml',
        'views/res_company_view.xml',
        'views/res_users.xml',
        'views/hr_plan_views.xml',
        'views/employee_information_agree.xml',
        'views/report_hr_probation_survey.xml',
        'wizard/employee_resume_print.xml',
        'wizard/employee_information_agree.xml',
        'wizard/employee_category_wizard.xml',
    ],
    'demo': [],
    'qweb': ["static/src/xml/nda_form.xml", "static/src/xml/coc_form.xml"],
    'images': ['static/description/icon.png'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
