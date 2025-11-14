{
    'name': 'POS Sales Summary Report (Date Range, Payment Split, Invoice Filter)',
    'version': '18.0.1.3.0',
    'summary': 'Reporte PDF de ventas POS por rango de fechas. Contado=Efectivo, Crédito=Otros métodos. Filtro por facturadas/NO facturadas.',
    'author': 'ChatGPT Assist',
    'website': '',
    'category': 'Point of Sale',
    'license': 'LGPL-3',
    'depends': ['point_of_sale', 'account', 'report_xlsx'],
    'data': [
        'security/ir.model.access.csv',
        'report/pos_sales_report.xml',
        'report/pos_sales_report_templates.xml',
        'report/pos_sales_report_xlsx.xml',   # 👈 NUEVO
        'views/pos_sales_report_wizard_view.xml',
    ],
    'application': False,
    'installable': True,
}