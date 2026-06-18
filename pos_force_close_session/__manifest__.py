# -*- coding: utf-8 -*-
{
    "name": "POS Force Close Session",
    "version": "18.0.1.0.2",
    "summary": "Permite cerrar sesión de PdV aun con facturas no publicadas (opción de publicar o anular/desvincular).",
    "category": "Point of Sale",
    "author": "TuEquipo",
    "website": "",
    "license": "LGPL-3",
    "depends": ["point_of_sale", "account"],
    "data": [
        "security/ir.model.access.csv",
        "views/pos_config_view.xml",
        "views/pos_session_view.xml",
        "views/pos_force_close_wizard_view.xml",
    ],
    "application": False,
    "installable": True,
}
