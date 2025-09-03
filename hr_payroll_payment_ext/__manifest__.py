
# -*- coding: utf-8 -*-
{
    'name': 'Payroll Payments from Batch (Community)',
    'summary': 'Create and track payments (including checks) directly from OCA payroll batches',
    'version': '18.0.1.0.4',
    'category': 'Human Resources/Payroll',
    'depends': ['payroll', 'account'],
    'author': 'Blockera Bustamante / ChatGPT',
    'website': 'https://example.com',
    'license': 'LGPL-3',
    'data': [
        'security/ir.model.access.csv',
        'views/hr_payroll_payment_views.xml',
    ],
    'installable': True,
    'application': False,
}
