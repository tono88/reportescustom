{
    "name": "Guatemala - Cheques Banrural / Epson LX-350",
    "summary": "Cheque personal calibrable y envío a la impresora USB con QZ Tray",
    "version": "18.0.1.0.0",
    "author": "Estuardo Sandoval",
    "website": "https://github.com/tono88/reportescustom",
    "license": "LGPL-3",
    "category": "Accounting/Localizations",
    "depends": ["l10n_gt_check_printing2", "web"],
    "external_dependencies": {"python": ["num2words"]},
    "data": [
        "reports/report_check.xml",
        "views/account_journal_views.xml",
        "views/account_payment_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "l10n_gt_check_printing2_lx350/static/src/printing.js",
            "l10n_gt_check_printing2_lx350/static/src/printing.xml",
        ],
    },
    "installable": True,
    "application": False,
}
