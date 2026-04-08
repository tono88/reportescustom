{
    'name': 'BB Import Purchase Order Lines',
    'version': '18.0.1.0.1',
    'summary': 'Importa líneas de órdenes de compra desde CSV/XLSX',
    'description': '''
Permite importar líneas de órdenes de compra/RFQ desde archivos CSV o XLSX.

Funciones principales:
- Botón en la orden de compra para abrir el asistente.
- Importación por CSV y Excel.
- Búsqueda de producto por referencia interna, código de barras o nombre.
- Soporte para columnas base: producto, descripción, cantidad, UDM, precio,
  impuestos y fecha prevista.
- Soporte opcional para campos extra por nombre técnico si el archivo lleva encabezados.
- Resumen de líneas creadas y filas omitidas.
''',
    'author': 'OpenAI',
    'license': 'LGPL-3',
    'category': 'Purchases',
    'depends': ['purchase'],
    'external_dependencies': {
        'python': ['openpyxl'],
    },
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/purchase_order_line_import_wizard_views.xml',
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
}
