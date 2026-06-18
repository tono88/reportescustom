# -*- coding: utf-8 -*-
import logging

from odoo import models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = "pos.session"

    def action_force_close_session(self):
        """Open the cleanup wizard when the POS configuration allows it."""
        self.ensure_one()
        if not self.config_id.allow_force_close:
            raise UserError(_("Activa 'Permitir cierre forzado' en la Configuración del PdV."))

        moves = self._get_blocking_moves()
        if not moves:
            return self.action_pos_session_closing_control()

        return {
            "type": "ir.actions.act_window",
            "name": _("Forzar cierre de sesión"),
            "res_model": "pos.force.close.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_session_id": self.id,
                "default_count_draft": len(moves.filtered(lambda m: m.state == "draft")),
                "default_count_cancel": len(moves.filtered(lambda m: m.state == "cancel")),
            },
        }

    def _get_session_orders(self):
        self.ensure_one()
        return self.env["pos.order"].sudo().search([("session_id", "=", self.id)])

    def _get_core_blocking_orders(self):
        """Return the exact orders used by Odoo's invoice-posting close check."""
        self.ensure_one()
        return self._get_closed_orders().sudo().filtered(
            lambda order: order.account_move and order.account_move.state != "posted"
        )

    def _get_blocking_moves(self):
        """Return draft/cancel invoices that can block the POS close.

        The first source deliberately mirrors Odoo's own
        ``_check_invoices_are_posted`` implementation. Extra relations are only
        included for compatibility with custom modules.
        """
        self.ensure_one()
        Order = self.env["pos.order"].sudo()
        Move = self.env["account.move"].sudo()
        orders = self._get_session_orders()
        move_ids = set(self._get_core_blocking_orders().mapped("account_move").ids)

        for field_name in ("account_move", "account_move_id"):
            field = Order._fields.get(field_name)
            if field and field.type == "many2one" and field.comodel_name == "account.move":
                move_ids.update(orders.mapped(field_name).ids)

        for field_name in ("pos_order_ids", "pos_orders_ids", "order_ids"):
            field = Move._fields.get(field_name)
            if field and field.comodel_name == "pos.order":
                move_ids.update(Move.search([(field_name, "in", orders.ids)]).ids)

        for field_name in ("pos_session_id", "session_id"):
            field = Move._fields.get(field_name)
            if field and field.type == "many2one" and field.comodel_name == "pos.session":
                move_ids.update(Move.search([(field_name, "=", self.id)]).ids)

        if not move_ids:
            return Move.browse([])

        return Move.search([
            ("id", "in", list(move_ids)),
            ("move_type", "in", ("out_invoice", "out_refund")),
            ("state", "in", ("draft", "cancel")),
        ])

    def _detach_blocking_moves(self, moves):
        """Detach cancelled/draft invoices without changing accounting data."""
        self.ensure_one()
        moves = moves.sudo().exists()
        if not moves:
            return

        Order = self.env["pos.order"].sudo()
        Move = self.env["account.move"].sudo()
        orders = self._get_session_orders()

        # Odoo's close check reads _get_closed_orders().account_move, so this is
        # the mandatory relation to clear. account_move_id is handled only when
        # a customization adds it as a second stored link.
        order_link_fields = []
        for field_name in ("account_move", "account_move_id"):
            field = Order._fields.get(field_name)
            if field and field.type == "many2one" and field.comodel_name == "account.move":
                order_link_fields.append(field_name)
                linked_orders = orders.filtered(
                    lambda order, fn=field_name: order[fn] and order[fn].id in moves.ids
                )
                if linked_orders:
                    linked_orders.write({field_name: False})

        # Optional direct session links supplied by custom modules.
        for field_name in ("pos_session_id", "session_id"):
            field = Move._fields.get(field_name)
            if field and field.type == "many2one" and field.comodel_name == "pos.session":
                linked_moves = moves.filtered(
                    lambda move, fn=field_name: move[fn] and move[fn].id == self.id
                )
                if linked_moves:
                    linked_moves.write({field_name: False})

        if order_link_fields:
            Order.flush_model(order_link_fields)
            orders.invalidate_recordset(order_link_fields)
        Move.flush_model()
        moves.invalidate_recordset()
        self.env.flush_all()
        self.env.invalidate_all()

        # Verify with exactly the same relation used by Odoo core.
        remaining_orders = self._get_core_blocking_orders()
        if remaining_orders:
            details = "\n".join(
                "%s → %s - %s" % (
                    order.display_name,
                    order.account_move.name or order.account_move.display_name,
                    order.account_move.state,
                )
                for order in remaining_orders
            )
            raise UserError(_(
                "No fue posible desvincular completamente las facturas de la sesión.\n"
                "Órdenes/facturas aún vinculadas:\n%s"
            ) % details)

        self.message_post(body=_(
            "Cierre forzado: se desvincularon %s factura(s) en borrador/canceladas. "
            "La sesión quedó lista para continuar con el cierre estándar."
        ) % len(moves))

    def _try_close_after_cleanup(self):
        """Continue with standard Odoo closing in a new HTTP transaction."""
        self.ensure_one()
        return self.action_pos_session_closing_control()
