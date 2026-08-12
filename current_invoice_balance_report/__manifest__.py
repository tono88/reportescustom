{
    "name": "Saldos por Fecha de Factura - Estado Actual",
    "summary": "Reporta facturas de un periodo usando su saldo y estado de pago actuales",
    "version": "18.0.1.0.0",
    "category": "Accounting/Accounting",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "views/current_balance_report_wizard_views.xml",
        "report/report_current_balance.xml",
    ],
    "installable": True,
    "application": False,
}
