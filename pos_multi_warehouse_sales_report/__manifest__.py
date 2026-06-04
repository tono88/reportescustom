# -*- coding: utf-8 -*-
{
    "name": "POS Multi Warehouse Sales Report",
    "version": "18.0.1.0.16",
    "category": "Point of Sale/Reporting",
    "summary": "Reporte de ventas POS agrupado por almacén y producto",
    "description": """
Reporte de ventas de Punto de Venta por almacén para instalaciones que usan
bi_pos_multi_warehouse. Permite filtrar por rango de fechas, cliente, estado de
facturación, almacén y compañía; muestra detalle por orden, producto, cantidad,
precio, cliente, cajero, número de factura, número DTE y totales. Incluye ventas POS facturadas y no facturadas según filtros, valida facturas canceladas, usa fecha fiscal para ventas facturadas y ajusta diferencias pequeñas de redondeo contra los totales oficiales de la factura contable solo en el filtro de facturados, mantiene totales POS en Todos y excluye reembolsos/orígenes de reembolso en todos los filtros.
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
