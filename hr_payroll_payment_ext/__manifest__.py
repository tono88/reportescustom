# -*- coding: utf-8 -*-
{
    'name': 'Payroll Payments from Batch (Community)',
    'summary': 'Create and track payments (including checks) from payroll batches and payslips, with explicit payment method selection',
    'version': '18.0.1.7.0',
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
