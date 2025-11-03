# -*- coding: utf-8 -*-
{
    "name": "Instant Reconcile & Fix Liquidity-Only Payment",
    "summary": "Reconciles payments on post and repairs liquidity-only entries (bank↔bank) by using partner AR/AP.",
    "version": "18.0.1.1.1",
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
    "auto_install": False
}