{
    "name": "Bank Reference Duplicate Check",
    "version": "18.0.1.0.2",
    "category": "Accounting",
    "summary": "Warn when bank_reference is already used on another payment",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "views/dup_bank_reference_wizard_views.xml",
        "views/account_payment_register_views.xml"
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
