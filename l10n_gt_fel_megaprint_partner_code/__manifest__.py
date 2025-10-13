# -*- coding: utf-8 -*-
{
    "name": "Megaprint FEL: Código interno de cliente en Reporte",
    "version": "18.0.1.0.0",
    "summary": "Muestra el código interno (res.partner.internal_code) en la sección Receptor del reporte FEL de Megaprint",
    "author": "ChatGPT Assist",
    "license": "LGPL-3",
    "category": "Accounting",
    "depends": [
        "l10n_gt_fel_megaprint_report",
        "partner_internal_code_v4"
    ],
    "data": [
        "reports/report_fel_partner_code.xml"
    ],
    "assets": {},
    "installable": True,
    "application": False
}