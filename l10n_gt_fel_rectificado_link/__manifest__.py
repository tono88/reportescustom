# -*- coding: utf-8 -*-
{
    "name": "GT FEL – Enlace a factura original en rectificaciones",
    "version": "18.0.1.0.1",
    "author": "Tu equipo",
    "license": "LGPL-3",
    "depends": ["account", "fel_megaprint"],
    "data": [],
    "post_init_hook": "post_init_set_original_links",
    "installable": True,
}
