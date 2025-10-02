# -*- coding: utf-8 -*-
{
    'name': "Pay Later in POS",
    'summary': 'Offer flexible Pay Later options for Point Of Sale',
    'author': "Srikesh Infotech",
    'license': "OPL-1",
    'website': "www.srikeshinfotech.com",
    'version': '1.1',
    'price': 35,
    'currency': 'EUR',
    'depends': ['account', 'point_of_sale'],
    'images': ['images/main_screenshot.png'],
    'assets': {
         'point_of_sale._assets_pos': [
            'skit_pay_later/static/src/**/*',
            ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
}