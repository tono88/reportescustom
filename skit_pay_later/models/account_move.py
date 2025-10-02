# -*- coding: utf-8 -*-

#import of odoo
from odoo import api, fields, models, _
from odoo.exceptions import  UserError

class AccountMove(models.Model):
    _inherit = 'account.move'

    is_pending_invoice = fields.Boolean('Current Invoice', default=False)


    # Inherit this method for show warning
    def action_register_payment(self):
        if self.pos_order_ids:
            raise UserError(_('You are not allowed to proceed. The order has been paid using Customer Account in POS.'))
        return super().action_register_payment()

    # get the pending invoice details into the current customer.
    @api.model
    def get_pending_invoice_details(self, invoice_id, payment_lines,
                                    pos_session):
        """ Get Invoice Details and payment process """
        order = self.env['pos.order'].search([
            ('account_move', '=', int(invoice_id))])
        session = self.env['pos.session'].browse(int(pos_session))
        account_journal = self.env['account.journal'].search([('type', '=', 'cash')])
        p_method = self.env['pos.payment.method'].search([('journal_id', 'in', account_journal.ids),
                                                          ('config_ids', 'in', session.config_id.ids)], limit=1)
        for pl in payment_lines:
            is_change = False
            if pl['paymethod'] == 0:
                amount = -(pl['amount'])
                payment_method_id = p_method.id
                name = p_method.name
                is_change = True
            else:
                amount = (pl['amount'])
                payment_method_id = pl['paymethod']
                name = pl['name']

            """  add payment methods for POS order under Payment tab
                create pos.payment  """
            current_date = fields.Date.from_string(fields.Date.today())
            args = {
                'amount': amount,
                'payment_date': current_date,
                'name': name + ': ',
                'pos_order_id': order.id,
                'payment_method_id': payment_method_id,
                'pos_session_id': session.id,
                'is_change': is_change
            }
            order.add_payment(args)
            order.account_move.update({'is_pending_invoice': True})
        for payment in order.payment_ids:
            if payment.pos_session_id:
                payment.update({'session_id': payment.pos_session_id.id})
        return True

