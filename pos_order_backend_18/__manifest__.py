# -*- coding: utf-8 -*-
{
    'name': 'POS Order Backend Print (Community)',
    'summary': 'Adds a printable PDF report for POS Orders in the backend and a Print button on the order form.',
    'version': '18.0.1.0.10',
    'category': 'Point of Sale',
    'author': 'ChatGPT Helper',
    'license': 'LGPL-3',
    'depends': ['point_of_sale'],
    'data': [
        'reports/pos_order_report_templates.xml',
        'reports/pos_order_report.xml',
        'views/pos_order_form_inherit.xml',
    ],
    'installable': True,
    'application': False,
}