# -*- coding: utf-8 -*-
{
    "name": "POS Receipt – Hide Prices",
    "summary": "Hide unit prices, line totals, taxes and grand totals on POS receipts (courier-friendly).",
    "version": "18.0.1.0.1",
    "author": "ChatGPT",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "data": [],
    "assets": {
        "point_of_sale.assets_prod": [
            "pos_receipt_hide_prices/static/src/app/generic_components/orderline/orderline.xml",
            "pos_receipt_hide_prices/static/src/app/screens/receipt_screen/receipt/hide_totals.xml",
        ],
        "point_of_sale.assets_debug": [
            "pos_receipt_hide_prices/static/src/app/generic_components/orderline/orderline.xml",
            "pos_receipt_hide_prices/static/src/app/screens/receipt_screen/receipt/hide_totals.xml",
        ],
    },
    "installable": True,
    "application": False,
}
