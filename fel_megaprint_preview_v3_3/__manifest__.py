# -*- coding: utf-8 -*-
{
    "name": "FEL Megaprint Preview v3.3",
    "summary": "Previsualiza SOLO el DTE dentro de <xml_dte><![CDATA[...]]> y lo muestra saneado. (Fix: usa fields.* en el wizard)",
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
