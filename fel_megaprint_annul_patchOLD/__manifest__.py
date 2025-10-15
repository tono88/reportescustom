# -*- coding: utf-8 -*-
{
    'name': 'FEL Megaprint – Anulación (Patch)',
    'version': '18.0.1.1.0',
    'category': 'Accounting/Localizations',
    'summary': 'Anular DTE FEL vía Megaprint (parche para Odoo 18, porta lógica 17.0)',
    'description': 'Añade botón en facturas para generar XML de anulación, firmar y enviar a Megaprint.',
    'author': 'Blockera Bustamante / ChatGPT',
    'license': 'LGPL-3',
    'depends': ['account', 'fel_gt', 'fel_megaprint'],
    'data': [
        'views/account_move_view.xml',
    ],
    'installable': True,
    'application': False
}
