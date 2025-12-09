# -*- coding: utf-8 -*-
{
    "name": "POS Receipt – Hide Prices (only on ticket)",
    "summary": "Hide prices, taxes and totals on the printed POS receipt, but keep them visible on the POS screen.",
    "version": "18.0.1.0.2",
    "author": "Estuardo / ChatGPT",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "data": [],
    "assets": {
        # Solo el recibo, nada de Orderline ni pantalla de venta
        "point_of_sale.assets_prod": [
            "pos_receipt_hide_prices/static/src/app/screens/receipt_screen/receipt/hide_totals.xml",
        ],
        "point_of_sale.assets_debug": [
            "pos_receipt_hide_prices/static/src/app/screens/receipt_screen/receipt/hide_totals.xml",
        ],
    },
    "installable": True,
    "application": False,
}
