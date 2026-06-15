# pos_internal_correlative/models/pos_order.py
import random
import time

from psycopg2 import OperationalError

from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    internal_correlative = fields.Char(
        string="Correlativo interno",
        index=True,
        copy=False,
    )

    def _next_correlative_for_session(self, session_id, invoiced=False):
        """Devuelve el siguiente número usando la secuencia del POS de la sesión.

        No genera números en create_from_ui(). La asignación queda centralizada
        en create() para evitar saltos por reintentos del POS.
        """
        if not session_id:
            return False

        session = self.env["pos.session"].browse(session_id).exists()
        if not session:
            return False

        config = session.config_id
        if not config:
            return False

        # Puede ejecutarse como cajero; las operaciones técnicas van con sudo.
        config.sudo()._ensure_internal_sequence()

        config_sudo = config.sudo()
        if invoiced:
            seq = (
                config_sudo.pos_internal_sequence_id
                or config_sudo.pos_internal_sequence_no_invoice_id
            )
        else:
            seq = (
                config_sudo.pos_internal_sequence_no_invoice_id
                or config_sudo.pos_internal_sequence_id
            )

        if not seq:
            return False

        seq_sudo = seq.sudo()
        # Si por historial la secuencia quedó como no_gap, puede lanzar:
        # "could not obtain lock on row in relation ir_sequence" cuando dos POS
        # consumen el mismo correlativo al mismo tiempo. Reintentamos dentro de
        # savepoint para no dejar abortada la transacción del pedido.
        for attempt in range(5):
            try:
                with self.env.cr.savepoint():
                    return seq_sudo.next_by_id()
            except OperationalError as exc:
                msg = str(exc).lower()
                if "could not obtain lock" not in msg and "lock not available" not in msg:
                    raise
                time.sleep(0.15 + random.random() * 0.25)
        # Último intento: si sigue bloqueada, dejamos que Odoo muestre el error real.
        return seq_sudo.next_by_id()

    @api.model
    def _order_fields(self, ui_order):
        """Permite aceptar el campo si alguna versión/parche del POS lo envía.

        No generamos números aquí. Solo copiamos un valor ya existente, porque
        este método puede ejecutarse dentro de flujos que luego se reintentan.
        """
        vals = super()._order_fields(ui_order)
        if ui_order.get("internal_correlative"):
            vals["internal_correlative"] = ui_order["internal_correlative"]
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("internal_correlative"):
                invoiced = bool(vals.get("to_invoice") or vals.get("is_invoiced"))
                correlative = self._next_correlative_for_session(
                    vals.get("session_id"),
                    invoiced=invoiced,
                )
                if not correlative:
                    correlative = self.env["ir.sequence"].sudo().next_by_code(
                        "pos.internal.correlative"
                    )
                if correlative:
                    vals["internal_correlative"] = correlative
        return super().create(vals_list)

    @api.model
    def create_from_ui(self, orders, draft=False):
        """No consumir secuencias antes del super.

        Antes el módulo hacía next_by_id() aquí y luego Odoo podía ignorar el
        campo o reintentar la orden, causando saltos grandes. La asignación real
        queda centralizada en create(). Al final solo devolvemos el correlativo
        al frontend si el formato de respuesta de Odoo lo permite.
        """
        result = super().create_from_ui(orders, draft=draft)

        if isinstance(result, list):
            ids = [
                r.get("id")
                for r in result
                if isinstance(r, dict) and r.get("id")
            ]
            if ids:
                by_id = {
                    order.id: order.internal_correlative
                    for order in self.browse(ids).exists()
                    if order.internal_correlative
                }
                for r in result:
                    if isinstance(r, dict) and r.get("id") in by_id:
                        r["internal_correlative"] = by_id[r["id"]]
        return result
