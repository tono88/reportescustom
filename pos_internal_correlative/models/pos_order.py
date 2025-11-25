# pos_internal_correlative/models/pos_order.py
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PosOrder(models.Model):
    _inherit = 'pos.order'

    internal_correlative = fields.Char(
        string='Correlativo interno',
        index=True,
        copy=False,
    )

    def _next_correlative_for_session(self, session_id, invoiced=False):
        """Devuelve el siguiente número usando la secuencia del POS de la sesión.

        :param invoiced: True si la orden se va a facturar, False si no.
        """
        if not session_id:
            return False
        session = self.env['pos.session'].browse(session_id)
        config = session.config_id
        if not config:
            return False
        # Asegura que las secuencias existan
        config._ensure_internal_sequence()

        # Elegir secuencia según si va facturada o no
        if invoiced:
            seq = config.pos_internal_sequence_id or config.pos_internal_sequence_no_invoice_id
        else:
            seq = config.pos_internal_sequence_no_invoice_id or config.pos_internal_sequence_id

        return seq.next_by_id() if seq else False

    @api.model
    def create(self, vals):
        if not vals.get('internal_correlative'):
            # Detectar si la orden viene marcada para facturarse
            invoiced = bool(vals.get('to_invoice') or vals.get('is_invoiced'))
            # si viene session_id en vals (backend / cron)
            correlative = self._next_correlative_for_session(
                vals.get('session_id'),
                invoiced=invoiced,
            )
            if not correlative:
                # Fallback: secuencia global (opcional)
                correlative = self.env['ir.sequence'].next_by_code('pos.internal.correlative')
            if correlative:
                vals['internal_correlative'] = correlative
        return super().create(vals)

    @api.model
    def create_from_ui(self, orders, draft=False):
        """
        UI: genera usando la secuencia del POS de la sesión (data.pos_session_id).
        """
        for o in orders:
            data = o.get('data') or {}

            if not data.get('internal_correlative'):
                # En los datos que manda el POS viene 'to_invoice' cuando el usuario marca "Facturar"
                invoiced = bool(data.get('to_invoice') or data.get('is_invoiced'))

                correlative = self._next_correlative_for_session(
                    data.get('pos_session_id'),
                    invoiced=invoiced,
                )
                if not correlative:
                    correlative = self.env['ir.sequence'].next_by_code('pos.internal.correlative')
                if correlative:
                    data['internal_correlative'] = correlative
        return super().create_from_ui(orders, draft=draft)
