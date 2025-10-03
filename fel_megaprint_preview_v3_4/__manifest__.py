# -*- coding: utf-8 -*-
{
    "name": "FEL Megaprint Preview v3.4",
    "summary": "Previsualiza SOLO el DTE dentro de <xml_dte><![CDATA[...]]>, saneado. Mockea otros POSTs con XML válido. (Fix: no retorna dict en requests.post)",
    "version": "18.0.1.4.0",
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
