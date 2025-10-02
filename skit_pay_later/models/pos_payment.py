# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
#  import from python lib
from odoo.exceptions import ValidationError

class PosPayment(models.Model):
    _inherit = 'pos.payment'

    pos_session_id = fields.Many2one('pos.session', string='POS Session')
    is_pay_later = fields.Boolean(string='Is Pay Later',
                                  related='payment_method_id.split_transactions',
                                  readonly=True)

    # override this method for avoid validation for pending order
    @api.constrains('amount')
    def _check_amount(self):
        for payment in self:
            if payment.pos_order_id.state in ['invoiced', 'done']:
                if payment.pos_order_id.session_id == payment.pos_session_id:
                    raise ValidationError(_('You cannot edit a payment for a posted order.'))

    # override this method for avoid validation for pending order
    @api.constrains('payment_method_id')
    def _check_payment_method_id(self):
        for payment in self:
            if payment.pos_session_id == payment.pos_order_id.session_id and payment.payment_method_id not in payment.session_id.config_id.payment_method_ids:
                raise ValidationError(_('The payment method selected is not allowed in the config of the POS session.'))

