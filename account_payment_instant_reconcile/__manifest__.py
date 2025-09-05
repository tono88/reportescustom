# -*- coding: utf-8 -*-
{
    "name": "Instant Reconcile on Payment (Community)",
    "summary": "Mark invoices as Paid immediately when posting payments, with a per-journal toggle.",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "license": "LGPL-3",
    "author": "Estuardo & ChatGPT",
    "website": "https://example.com",
    "depends": ["account"],
    "data": [
        "views/account_journal_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}