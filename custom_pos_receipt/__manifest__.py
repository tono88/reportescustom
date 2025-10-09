# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

{
    'name': 'POS Custom Receipt',
    'version': '18.0.1.1',
    "license": "OPL-1",
    'category': 'Sales/Point of Sale',
    'author': 'Kanak Infosystems LLP.',
    'website': 'https://www.kanakinfosystems.com',
    'summary': 'This module is used to customized receipt of point of sale when a user adds a product in the cart and validates payment and print receipt, then the user can see the client name on POS Receipt. | Custom Receipt | POS Reciept | Payment | POS Custom Receipt',
    'description': "Customized our point of sale receipt.",
    'depends': ['base', 'point_of_sale'],
    'assets': {
        'web.assets_qweb': [
            'custom_pos_receipt/static/src/xml/*.xml'
        ],
        'point_of_sale.assets_prod': [
            'custom_pos_receipt/static/src/overrides/pos_store_header_patch.js',
            'custom_pos_receipt/static/src/overrides/pos_order_correlative.js'
        ],
        'point_of_sale.assets': [
            'custom_pos_receipt/static/src/overrides/pos_store_header_patch.js',
            'custom_pos_receipt/static/src/overrides/pos_order_correlative.js'
        ],
        'point_of_sale._assets_pos': [
            'custom_pos_receipt/static/src/js/models.js',
            'custom_pos_receipt/static/src/xml/pos.xml',
        ],
    },
    'images': ['static/description/banner.jpg'],
    'installable': True,
}
