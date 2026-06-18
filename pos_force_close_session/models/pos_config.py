# -*- coding: utf-8 -*-
from odoo import models, fields

class PosConfig(models.Model):
    _inherit = "pos.config"

    allow_force_close = fields.Boolean(
        string="Permitir cierre forzado con facturas no publicadas",
        help="Si está activo, podrás usar el botón 'Forzar cierre' en la sesión para "
             "publicar o anular/desvincular facturas en borrador/canceladas."
    )
