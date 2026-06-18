# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class PosForceCloseWizard(models.TransientModel):
    _name = "pos.force.close.wizard"
    _description = "Forzar cierre de sesión de PdV"

    session_id = fields.Many2one("pos.session", required=True, ondelete="cascade")
    action_mode = fields.Selection(
        [
            ("post", "Publicar todas las facturas en borrador"),
            ("cancel_unlink", "Anular y desvincular de la sesión"),
        ],
        string="Acción a ejecutar",
        default="cancel_unlink",
        required=True,
        help=(
            "• Publicar: intentará publicar todas las facturas en borrador.\n"
            "• Anular y desvincular: cancelará borradores y quitará las relaciones "
            "POS que bloquean el cierre."
        ),
    )
    count_draft = fields.Integer(readonly=True)
    count_cancel = fields.Integer(readonly=True)
    cleanup_done = fields.Boolean(readonly=True, default=False)

    def _reopen_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Forzar cierre de sesión"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_apply(self):
        """Clean invoice links only; do not start accounting close yet.

        Odoo can explicitly roll back the transaction when it detects an
        unbalanced POS closing entry and opens its balancing wizard. Starting
        that close in this same request would undo the cleanup. The second step
        therefore starts the standard close in a separate request.
        """
        self.ensure_one()
        session = self.session_id.sudo()
        moves = session._get_blocking_moves().sudo()

        if self.action_mode == "post":
            drafts = moves.filtered(lambda move: move.state == "draft")
            if drafts:
                drafts._post()
            moves = session._get_blocking_moves().sudo()

        drafts = moves.filtered(lambda move: move.state == "draft")
        if drafts:
            drafts.button_cancel()

        moves = session._get_blocking_moves().sudo()
        session._detach_blocking_moves(moves)

        self.write({
            "cleanup_done": True,
            "count_draft": 0,
            "count_cancel": 0,
        })
        return self._reopen_wizard()

    def action_continue_close(self):
        """Start Odoo's standard close after cleanup has been committed."""
        self.ensure_one()
        if not self.cleanup_done:
            raise UserError(_("Primero debe aplicar la limpieza de facturas."))

        session = self.session_id.sudo()
        remaining_orders = session._get_core_blocking_orders()
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
                "Todavía existen facturas no publicadas vinculadas a la sesión:\n%s"
            ) % details)

        return session._try_close_after_cleanup()
