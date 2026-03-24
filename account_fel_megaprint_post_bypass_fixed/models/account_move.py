from odoo import _, models
from odoo.exceptions import UserError
from odoo.addons.account.models.account_move import AccountMove as AccountMoveCore


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _fel_bypass_context(self):
        return {
            'skip_fel_certification': True,
            'skip_gt_fel_certification': True,
            'skip_megaprint_fel_certification': True,
            'bypass_fel_certification': True,
            'post_without_fel_certification': True,
            'fel_megaprint_post_bypass': True,
        }

    def _is_megaprint_bypass_active(self):
        ctx = self.env.context
        return any(bool(ctx.get(flag)) for flag in self._fel_bypass_context().keys())

    def _fel_reference_field_names(self):
        return [
            'firma_fel',
            'serie_fel',
            'numero_fel',
            'numero_autorizacion',
            'uuid',
            'fel_uuid',
            'x_fel_uuid',
            'x_numero_autorizacion',
            'xml_fel',
            'resultado_xml_fel',
            'documento_xml_fel',
        ]

    def _has_any_fel_reference(self):
        self.ensure_one()
        for field_name in self._fel_reference_field_names():
            if field_name in self._fields and self[field_name]:
                return True
        return False

    def _validate_bypass_allowed(self):
        for move in self:
            if move.state != 'draft':
                raise UserError(_("Solo se puede usar en documentos en borrador."))
            if move.move_type not in ('out_invoice', 'out_refund'):
                raise UserError(_("Solo aplica a facturas o notas de crédito de cliente."))
            if not move._has_any_fel_reference():
                raise UserError(_(
                    "No encontré datos FEL previos en la factura. "
                    "Por seguridad, el bypass solo se permite en documentos que ya tengan evidencia FEL guardada."
                ))

    def action_post_without_fel(self):
        self._validate_bypass_allowed()
        moves = self.with_context(**self._fel_bypass_context())
        AccountMoveCore._post(moves, soft=False)
        moves.filtered(lambda m: m.state == 'posted').message_post(
            body=_(
                "Documento contabilizado por bypass administrativo sin volver a recertificar FEL Megaprint."
            )
        )
        return True

    def _post(self, soft=True):
        if self._is_megaprint_bypass_active():
            return AccountMoveCore._post(self, soft=soft)
        return super()._post(soft=soft)

    def certificar_megaprint(self, *args, **kwargs):
        if self._is_megaprint_bypass_active():
            return True
        return super().certificar_megaprint(*args, **kwargs)
