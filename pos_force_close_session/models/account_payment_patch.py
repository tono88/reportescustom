# -*- coding: utf-8 -*-
from odoo import models

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # Shim de compatibilidad: aceptar kwargs extra (p.ej. force_balance) que
    # algunos módulos/series nuevas envían al cerrar la sesión del POS.
    def _prepare_move_line_default_vals(self, write_off_line_vals=None, **kwargs):
        # Descarta parámetros que tu versión no espera
        kwargs.pop('force_balance', None)
        # Llama al core con la firma clásica
        return super(AccountPayment, self)._prepare_move_line_default_vals(
            write_off_line_vals=write_off_line_vals
        )
