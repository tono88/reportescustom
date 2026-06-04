# -*- coding: utf-8 -*-
{
    "name": "POS Refund No Stock by Reference",
    "version": "18.0.1.0.0",
    "summary": "Crea reembolsos POS pagados desde Excel sin generar movimientos de inventario.",
    "author": "Velfasa / ChatGPT",
    "license": "LGPL-3",
    "category": "Point of Sale",
    "depends": ["point_of_sale"],
    "data": [
        "security/ir.model.access.csv",
        "views/pos_refund_no_stock_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
}
