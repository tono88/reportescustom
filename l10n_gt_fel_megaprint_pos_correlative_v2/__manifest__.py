# -*- coding: utf-8 -*-
{
    "name": "Megaprint FEL: Correlativo POS en Reporte",
    "version": "18.0.1.0.1",
    "summary": "Inserta el correlativo interno del POS en el bloque DTE del reporte FEL (Megaprint)",
    "author": "ChatGPT Assist",
    "license": "LGPL-3",
    "category": "Accounting",
    "depends": ["l10n_gt_fel_megaprint_report", "pos_internal_correlative"],
    "data": ["reports/report_fel_invoice_extend.xml"],
    "assets": {},
    "installable": True,
    "application": False
}