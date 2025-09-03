# -*- coding: utf-8 -*-
{
    'name': 'Payroll Payments from Batch (Community)',
    'summary': 'Create and track payments (including checks) directly from OCA payroll batches and individual payslips',
    'version': '18.0.1.1.0',
    'category': 'Human Resources/Payroll',
    'depends': ['payroll', 'account'],
    'author': 'Blockera Bustamante / ChatGPT',
    'website': 'https://example.com',
    'license': 'LGPL-3',
    'data': [
        'security/ir.model.access.csv',
        'views/hr_payroll_payment_views.xml',
        'views/hr_payslip_payment_views.xml',
    ],
    'installable': True,
    'application': False,
}
