# pos_internal_correlative/models/pos_order.py
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PosOrder(models.Model):
    _inherit = 'pos.order'

    internal_correlative = fields.Char(string='Correlativo interno', index=True, copy=False)

    def _next_correlative_for_session(self, session_id):
        """Devuelve el siguiente número usando la secuencia del POS de la sesión."""
        if not session_id:
            return False
        session = self.env['pos.session'].browse(session_id)
        config = session.config_id
        if not config:
            return False
        # Asegura que la secuencia exista
        config._ensure_internal_sequence()
        seq = config.pos_internal_sequence_id
        return seq.next_by_id() if seq else False

    @api.model
    def create(self, vals):
        if not vals.get('internal_correlative'):
            # si viene session_id en vals (backend / cron)
            correlative = self._next_correlative_for_session(vals.get('session_id'))
            if not correlative:
                # Fallback: si por alguna razón no hay sesión, intenta la secuencia global (opcional)
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
                correlative = self._next_correlative_for_session(data.get('pos_session_id'))
                if not correlative:
                    correlative = self.env['ir.sequence'].next_by_code('pos.internal.correlative')
                if correlative:
                    data['internal_correlative'] = correlative
        return super().create_from_ui(orders, draft=draft)
