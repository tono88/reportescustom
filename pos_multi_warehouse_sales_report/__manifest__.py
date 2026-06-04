# -*- coding: utf-8 -*-
{
    "name": "POS Multi Warehouse Sales Report",
    "version": "18.0.1.0.9",
    "category": "Point of Sale/Reporting",
    "summary": "Reporte de ventas POS agrupado por almacén y producto",
    "description": """
Reporte de ventas de Punto de Venta por almacén para instalaciones que usan
bi_pos_multi_warehouse. Permite filtrar por rango de fechas, cliente, estado de
facturación, almacén y compañía; muestra detalle por orden, producto, cantidad,
precio, cliente, cajero, número de factura, número DTE y totales. Excluye órdenes POS marcadas como facturadas cuando la factura relacionada no existe, está cancelada o tiene una nota de crédito de cliente relacionada.
    """,
    "author": "Tecnodyne",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
        "stock",
        "account",
        "bi_pos_multi_warehouse",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/pos_warehouse_sales_report_views.xml",
        "views/pos_warehouse_sales_report_menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
