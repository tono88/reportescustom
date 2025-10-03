# -*- coding: utf-8 -*-
{
    "name": "FEL Megaprint Preview",
    "summary": "Previsualiza el XML DTE (factura) antes de enviar. Mockea endpoints no objetivo con XML válido.",
    "version": "18.0.1.3.0",
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
