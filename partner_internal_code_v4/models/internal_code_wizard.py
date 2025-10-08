from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ResPartnerInternalCodeWizard(models.TransientModel):
    _name = 'res.partner.internal.code.wizard'
    _description = 'Asignar códigos internos a clientes existentes'

    scope = fields.Selection([
        ('all', 'Todos los clientes sin código'),
        ('selected', 'Solo los seleccionados en la lista'),
    ], string='Alcance', default='all', required=True)
    processed = fields.Integer(string='Procesados', readonly=True)
    assigned = fields.Integer(string='Asignados', readonly=True)

    def action_assign(self):
        self.ensure_one()
        domain = [('customer_rank', '>', 0), ('internal_code', '=', False)]

        # Si se elige “Seleccionados” desde la vista lista
        if self.scope == 'selected':
            active_ids = self.env.context.get('active_ids', [])
            if not active_ids:
                raise UserError(_('No hay contactos seleccionados.'))
            domain.append(('id', 'in', active_ids))

        partners = self.env['res.partner'].search(domain)
        assigned = 0
        for partner in partners:
            partner._assign_internal_code_if_needed()
            assigned += 1

        self.write({'processed': len(partners), 'assigned': assigned})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Códigos internos asignados'),
                'message': _('Procesados: %s | Asignados: %s') % (len(partners), assigned),
                'type': 'success',
                'sticky': False,
            }
        }
