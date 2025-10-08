# -*- coding: utf-8 -*-
{
    'name': 'Partner Internal Code',
    'summary': "Código interno secuencial para clientes; búsqueda y asignación masiva.",
    'version': '18.0.2.0.1',
    'category': 'Contacts',
    'author': 'Blockera Bustamante / ChatGPT',
    'license': 'LGPL-3',
    'website': 'https://example.com',
    'depends': ['base', 'contacts', 'point_of_sale'],  # quita 'point_of_sale' si no lo usas
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/internal_code_wizard_views.xml',  # <-- primero
        'views/res_partner_views.xml',           # <-- después
    ],
    'assets': {
        'point_of_sale.assets': [
            'partner_internal_code_v4/static/src/js/pos_partner_internal_code.js',
            # No cargues ningún XML del POS por ahora
        ],
    },
    'installable': True,
    'application': False,
}
