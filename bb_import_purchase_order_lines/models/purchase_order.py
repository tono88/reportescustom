from odoo import _, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_open_import_lines_wizard(self):
        self.ensure_one()
        if not self.id:
            raise UserError(_('Primero debes guardar la orden de compra.'))
        if self.state not in ('draft', 'sent'):
            raise UserError(_('Solo se permite importar líneas en RFQ u órdenes en borrador.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Importar líneas'),
            'res_model': 'purchase.order.line.import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_purchase_id': self.id,
            },
        }
