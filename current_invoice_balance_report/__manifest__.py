# -*- coding: utf-8 -*-
{
    "name": "Saldos por Fecha - Estado Actual",
    "summary": "Saldos actuales de clientes/proveedores; facturados y pedidos POS no facturados; exportación XLSX",
    "version": "18.0.1.2.0",
    "category": "Accounting/Accounting",
    "author": "Tecnodyne",
    "license": "LGPL-3",
    "depends": ["account", "point_of_sale"],
    "data": [
        "security/ir.model.access.csv",
        "views/current_balance_report_wizard_views.xml",
        "report/report_current_balance.xml",
    ],
    "installable": True,
    "application": False,
}
