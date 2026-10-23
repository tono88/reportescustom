{
    "name": "Cheques personales PDF Banrural y G&T — Importable",
    "summary": "XML y activos estáticos: cheques personales con barra de ajuste del monto",
    "version": "18.0.1.0.14",
    "author": "Estuardo Sandoval",
    "website": "https://github.com/tono88/reportescustom",
    "license": "LGPL-3",
    "category": "Accounting/Localizations",
    "depends": ["l10n_gt_check_printing2", "web"],
    "data": ["reports/check_reports.xml", "views/payment_buttons.xml"],
    "assets": {
        "web.assets_backend": ["l10n_gt_check_printing2_pdf_live/static/src/amount_position.js"],
    },
    "installable": True,
    "application": False,
}
