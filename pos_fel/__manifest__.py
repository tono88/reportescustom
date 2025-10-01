# -*- coding: utf-8 -*-

{
    'name': 'Point of Sale unido a facturacion electrónica',
    'version': '2.7',
    'category': 'Point of Sale',
    'sequence': 6,
    'summary': 'Point of Sale unido a facturacion electrónica',
    'description': """ Cambios al Punto de Venta para generar facturas electrónicas fácilmente """,
    'website': 'http://aquih.com',
    'author': 'aquíH',
    'depends': ['point_of_sale', 'fel_gt'],
    'data': [],
    'installable': True,
    'auto_install': False,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_fel/static/src/**/*',
        ],
    },
    'license': 'Other OSI approved licence',
}
