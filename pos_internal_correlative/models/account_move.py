# pos_internal_correlative/models/account_move.py
from odoo import api, fields, models

class AccountMove(models.Model):
    _inherit = 'account.move'

    internal_correlative = fields.Char(string='Correlativo interno POS', index=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        pos_orders = self.env['pos.order'].search([('account_move', 'in', moves.ids)])
        order_by_move = {o.account_move.id: o for o in pos_orders if o.account_move}
        for move in moves:
            if not move.internal_correlative:
                order = order_by_move.get(move.id)
                if order and order.internal_correlative:
                    move.internal_correlative = order.internal_correlative
        return moves
