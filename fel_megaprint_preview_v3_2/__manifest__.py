# -*- coding: utf-8 -*-
{
    "name": "FEL Megaprint Preview v3.2",
    "summary": "Previsualiza SOLO el DTE dentro de <xml_dte><![CDATA[...]]> y lo muestra ya SANITIZADO (sin Frase 4 ni impuestos en 0).",
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
