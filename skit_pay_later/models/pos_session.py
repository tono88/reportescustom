# -*- coding: utf-8 -*-

#  import from odoo lib
from odoo import fields, models, _
from odoo.exceptions import AccessError

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _confirm_paylater_orders(self, session_id):
        """ Posting method for Pay later order while close session
                :param pay_later_order:order
                 """
        pos_payment_method = self.env['pos.payment.method'].search(
            [('split_transactions', '=', True)])
        pos_payment = self.env['pos.payment'].search(
            [('pos_session_id', '=', int(session_id)),
             ('payment_method_id', '!=', pos_payment_method.id)]
        )
        order_ids = []
        for payment in pos_payment:
            if payment.session_id.id == session_id:
                order_ids.append(int(payment.pos_order_id.id))
        pay_order = self.env['pos.order'].search([
            ('id', 'in', order_ids),
            ('session_id', '!=', session_id),
            ('state', 'in', ('invoiced', 'done'))])
        for order in pay_order:
            account_move_line = self.env['account.move.line'].with_context(check_move_validity=False)
            pos_payment = order.payment_ids.filtered(lambda p: not p.account_move_id and p.payment_method_id.type != 'pay_later')
            change_payment = pos_payment.filtered(lambda p: p.is_change and not p.account_move_id and p.payment_method_id.type == 'cash')
            payment_to_change = pos_payment.filtered(lambda p: not p.is_change and not p.account_move_id and p.payment_method_id.type == 'cash')[:1]
            for payment in pos_payment - change_payment:
                order = payment.pos_order_id
                payment_method = payment.payment_method_id
                accounting_partner = self.env["res.partner"]._find_accounting_partner(payment.partner_id)
                pos_session = order.session_id
                journal = pos_session.config_id.journal_id
                if change_payment and payment == payment_to_change:
                    pos_payment_ids = payment.ids + change_payment.ids
                    payment_amount = payment.amount + change_payment.amount
                else:
                    pos_payment_ids = payment.ids
                    payment_amount = payment.amount
                reversed_move_receivable_account_id = payment.company_id.account_default_pos_receivable_account_id.id
                move = self.env['account.move'].with_context(default_journal_id=journal.id).create({
                    'journal_id': self.config_id.journal_id.id,
                    'date': fields.Date.context_today(order, order.date_order),
                    'ref': _('Invoice payment for %s (%s) using %s', order.name, order.account_move.name,
                             payment_method.name),
                    'pos_payment_ids': pos_payment_ids,
                })
                combile_vals = {
                    'move_id': move.id,
                    'move_name': move.name,
                    'ref': self.name,
                    'account_id': reversed_move_receivable_account_id,
                    'session_id': session_id,
                    'partner_id': self.env["res.partner"]._find_accounting_partner(payment.partner_id).id,
                    'name': '%s - %s' % (self.name, payment.payment_method_id.name),
                    'debit': payment_amount,
                    'credit': 0,
                    'is_pay_later': True,
                }
                account_move_line.create(combile_vals)
                invoice_vals = {
                    'move_id': move.id,
                    'move_name': move.name,
                    'ref': self.name,
                    'account_id': accounting_partner.with_company(order.company_id).property_account_receivable_id.id,
                    'name': 'From invoiced orders',
                    'credit': payment_amount,
                    'debit': 0,
                    'is_pay_later': True,
                }
                # From Invoice order lines
                m_lines = account_move_line.create(invoice_vals)

                invoice_line_receivable = self.env['account.move.line'].search(
                    [('move_id', '=', order.account_move.id),
                     ('account_type', '=', 'asset_receivable')])
                # Post the records after i will check reconcile
                if move.line_ids:
                    move.action_post()
                    (m_lines | invoice_line_receivable).reconcile()
                    # Set the uninvoiced orders' state to 'done'
                else:
                    move.unlink()

    # Inherit the session close action and confirm the order
    def action_pos_session_close(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        res = super(PosSession, self).action_pos_session_close()
        session_id = self.id
        self._confirm_paylater_orders(session_id)
        return res

    def get_closing_control_data(self):
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessError(_("You don't have the access rights to get the point of sale closing control data."))
        self.ensure_one()
        orders = self._get_closed_orders()
        payments = orders.payment_ids.filtered(lambda p: p.payment_method_id.type != "pay_later")
        paylater_payments = self.env['pos.payment'].search([('pos_session_id', '=', self.id)])
        payments = payments + paylater_payments
        other_payment_ids = orders.payment_ids + paylater_payments
        cash_payment_method_ids = self.payment_method_ids.filtered(lambda pm: pm.type == 'cash')
        default_cash_payment_method_id = cash_payment_method_ids[0] if cash_payment_method_ids else None
        default_cash_payments = payments.filtered(lambda p: p.payment_method_id == default_cash_payment_method_id) if default_cash_payment_method_id else []
        total_default_cash_payment_amount = sum(default_cash_payments.mapped('amount')) if default_cash_payment_method_id else 0
        non_cash_payment_method_ids = self.payment_method_ids - default_cash_payment_method_id if default_cash_payment_method_id else self.payment_method_ids
        non_cash_payments_grouped_by_method_id = {pm: other_payment_ids.filtered(lambda p: p.payment_method_id == pm) for pm in non_cash_payment_method_ids}

        cash_in_count = 0
        cash_out_count = 0
        cash_in_out_list = []
        for cash_move in self.sudo().statement_line_ids.sorted('create_date'):
            if cash_move.amount > 0:
                cash_in_count += 1
                name = f'Cash in {cash_in_count}'
            else:
                cash_out_count += 1
                name = f'Cash out {cash_out_count}'
            cash_in_out_list.append({
                'name': cash_move.payment_ref if cash_move.payment_ref else name,
                'amount': cash_move.amount
            })

        return {
            'orders_details': {
                'quantity': len(orders),
                'amount': sum(orders.mapped('amount_total'))
            },
            'opening_notes': self.opening_notes,
            'default_cash_details': {
                'name': default_cash_payment_method_id.name,
                'amount': self.cash_register_balance_start
                          + total_default_cash_payment_amount
                          + sum(self.sudo().statement_line_ids.mapped('amount')),
                'opening': self.cash_register_balance_start,
                'payment_amount': total_default_cash_payment_amount,
                'moves': cash_in_out_list,
                'id': default_cash_payment_method_id.id
            } if default_cash_payment_method_id else {},
            'non_cash_payment_methods': [{
                'name': pm.name,
                'amount': sum(non_cash_payments_grouped_by_method_id[pm].mapped('amount')),
                'number': len(non_cash_payments_grouped_by_method_id[pm]),
                'id': pm.id,
                'type': pm.type,
            } for pm in non_cash_payment_method_ids],
            'is_manager': self.env.user.has_group("point_of_sale.group_pos_manager"),
            'amount_authorized_diff': self.config_id.amount_authorized_diff if self.config_id.set_maximum_difference else None
        }

