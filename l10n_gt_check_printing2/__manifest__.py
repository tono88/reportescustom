# -*- coding: utf-8 -*-
{
    "name": "Guatemala - Check Printing 2",
    "summary": "Formato de cheque Guatemala con proveedor alineado, corrimientos de fecha/monto y monto en letras en una sola línea.",
    "version": "18.0.2.0.2",
    "author": "Estuardo Sandoval & ChatGPT",
    "website": "https://example.com",
    "category": "Accounting/Localizations",
    "license": "LGPL-3",
    "depends": ["account", "account_check_printing"],
    "data": [
        "security/ir.model.access.csv",
        "reports/paperformat.xml",
        "reports/report_check_templates.xml"
    ],
    "assets": {},
    "installable": True,
    "application": False,
    "auto_install": False
}
