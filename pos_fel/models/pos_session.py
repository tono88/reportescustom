# -*- encoding: utf-8 -*-

import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class PosSession(models.Model):
    _inherit = 'pos.session'

    def action_pos_session_close(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        for session in self:
            if session.config_id.invoice_journal_id and session.config_id.invoice_journal_id.generar_fel:
                if len(session.order_ids.filtered(lambda order: order.state not in ['invoiced', 'cancel'] and not order.currency_id.is_zero(order.amount_total))) > 0:
                    raise ValidationError('Tiene pedidos sin factura, no puede cerrar sesión mientras no haya facturado todos los pedidos.')
                for order in session.order_ids.filtered(lambda order: order.state == 'invoiced' and not order.currency_id.is_zero(order.amount_total)):
                    if order.account_move.state != 'open' and not order.account_move.firma_fel:
                        raise ValidationError('La factura del pedido {} no está firmada, por favor ingrese a la factura y validela para poder cerrar sesión.'.format(order.name))

        return super(PosSession, self).action_pos_session_close(balancing_account, amount_to_balance, bank_payment_method_diffs)

    @api.model
    def crear_partner_con_datos_sat(self, company_id, vat):
        if company_id:
            company = self.env['res.company'].search([('id','=',company_id)])
            partners = self.env['res.partner'].search([('vat','=',vat)])

            # Si el partner no existe se crea y si ya existe, se devuelve el que ya existe
            if len(partners) == 0:
                datos_facturacion_fel = self.env['res.partner'].obtener_datos_facturacion_fel(company, vat)
                if datos_facturacion_fel['nombre'] and datos_facturacion_fel['nit']:
                    partner_dic = {
                        'name': datos_facturacion_fel['nombre'],
                        'vat': datos_facturacion_fel['nit'],
                    }
                    new_partner = self.env['res.partner'].create(partner_dic)
                    return new_partner.read([])
                else:
                    return []
            else:
                return partners.read([])
        else:
            return []
