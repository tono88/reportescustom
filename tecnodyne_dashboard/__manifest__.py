{
    'name': 'Tecnodyne Dashboards',
    'summary': 'Configurable company dashboards using the Odoo security model',
    'version': '18.0.1.0.0',
    'author': 'Tecnodyne',
    'license': 'LGPL-3',
    'depends': ['web'],
    'data': ['security/security.xml', 'security/ir.model.access.csv',
             'views/dashboard_views.xml', 'wizard/transfer_views.xml'],
    'assets': {'web.assets_backend': [
        'tecnodyne_dashboard/static/src/dashboard.js',
        'tecnodyne_dashboard/static/src/dashboard.xml',
        'tecnodyne_dashboard/static/src/dashboard.scss',
    ]},
    'application': True,
    'installable': True,
}
