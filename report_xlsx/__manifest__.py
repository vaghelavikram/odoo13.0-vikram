# Copyright 2015 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    "name": "Banas Tech report xlsx",
    "summary": "Base module to create xlsx report",
    "author": "Banas Tech PVT Ltd",
    "website": "https://github.com/oca/reporting-engine",
    "category": "Reporting",
    "version": "0.1",
    "license": "AGPL-3",
    "external_dependencies": {"python": ["xlsxwriter", "xlrd"]},
    "depends": ["base", "web"],
    # "data": ["views/webclient_templates.xml"],
    "demo": ["demo/report.xml"],
    "installable": True,
}
