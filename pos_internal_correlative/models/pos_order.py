# pos_internal_correlative/models/pos_order.py
from odoo import api, fields, models, _


class PosOrder(models.Model):
    _inherit = 'pos.order'

    internal_correlative = fields.Char(
        string='Correlativo interno',
        index=True,
        copy=False,
    )

    def _next_correlative_for_session(self, session_id, invoiced=False):
        """Devuelve el siguiente número usando la secuencia del POS de la sesión.

        IMPORTANTE: este método debe llamarse únicamente cuando realmente se va
        a crear/escribir la orden, no antes de llamar a create_from_ui(), para
        evitar saltos por reintentos del POS o errores posteriores de factura.
        """
        if not session_id:
            return False
        session = self.env['pos.session'].browse(session_id).exists()
        if not session:
            return False
        config = session.config_id
        if not config:
            return False

        config._ensure_internal_sequence()

        if invoiced:
            seq = config.pos_internal_sequence_id or config.pos_internal_sequence_no_invoice_id
        else:
            seq = config.pos_internal_sequence_no_invoice_id or config.pos_internal_sequence_id

        return seq.next_by_id() if seq else False

    @api.model
    def _order_fields(self, ui_order):
        """Permite aceptar el campo si alguna versión/parche del POS lo envía.

        No generamos números aquí. Solo copiamos un valor ya existente, porque
        este método puede ejecutarse dentro de flujos que luego se reintentan.
        """
        vals = super()._order_fields(ui_order)
        if ui_order.get('internal_correlative'):
            vals['internal_correlative'] = ui_order['internal_correlative']
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('internal_correlative'):
                invoiced = bool(vals.get('to_invoice') or vals.get('is_invoiced'))
                correlative = self._next_correlative_for_session(
                    vals.get('session_id'),
                    invoiced=invoiced,
                )
                if not correlative:
                    correlative = self.env['ir.sequence'].next_by_code('pos.internal.correlative')
                if correlative:
                    vals['internal_correlative'] = correlative
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
            ids = [r.get('id') for r in result if isinstance(r, dict) and r.get('id')]
            if ids:
                by_id = {
                    order.id: order.internal_correlative
                    for order in self.browse(ids).exists()
                    if order.internal_correlative
                }
                for r in result:
                    if isinstance(r, dict) and r.get('id') in by_id:
                        r['internal_correlative'] = by_id[r['id']]
        return result
