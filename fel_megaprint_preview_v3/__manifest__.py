# -*- coding: utf-8 -*-
{
    "name": "FEL Megaprint Preview",
    "summary": "Previsualiza el XML DTE (el que contiene la factura) antes de enviarlo (no crea adjuntos, no llama a red).",
    "version": "18.0.1.2.0",
    "author": "ChatGPT",
    "depends": ["account", "fel_megaprint"],
    "data": [
        "security/ir.model.access.csv",
        "views/account_move_views.xml",
        "views/preview_wizard_views.xml"
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False
}
