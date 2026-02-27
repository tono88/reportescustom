# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

{
    "name": "Database Auto Backup - Google Drive",
    "version": "18.0.1.2",
    'license': 'OPL-1',
    "depends": ["base"],
    "category": "Tools",
    "author": "Kanak Infosystems LLP.",
    "website": "https://www.kanakinfosystems.com",
    "summary": """Database Auto Backup - Google Drive""",
    "description": """Database Auto Backup - Google Drive""",
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/db_automatic_backup_rules_views.xml",
        "views/db_backup_destination_views.xml",
        "views/ir_ui_menu.xml"
    ],
    'images': ['static/description/banner.gif'],
    "application": True,
    "installable": True,
    "price": 29.0,
    "currency": "EUR",
}
