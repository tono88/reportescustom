# -*- coding: utf-8 -*-
#imports of odoo
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_round


#Inheriting the PosOrder model
class PosOrder(models.Model):
    _inherit = 'pos.order'


    is_pay_later = fields.Boolean('Is Paylater', default=False)

    def add_payment(self, data):
        """Create a new payment for the order"""
        res = super(PosOrder, self).add_payment(data)
        amount = 0
        for pay in self.payment_ids:
            if pay.is_pay_later:
                pay.pos_order_id.is_pay_later = True
            else:
                amount += pay.amount
        self.amount_paid = amount
        return res

    @api.model
    def fetch_partner_order(self, customer, session_id):
        """ Serialize the orders of the customer

        params: customer int representing the customer id
        """
        params = {'partner_id': customer}
        # Generate Order Details
        sql_query = """ select  x.order_id, x.date_order, x.type  from (
                            select id as order_id,date_order,'POS'as type
                            from pos_order
                            where partner_id = %(partner_id)s
                            )
                            as x order by x.date_order desc"""

        self._cr.execute(sql_query, params)
        rows = self._cr.dictfetchall()
        datas = self.get_order_datas(rows, session_id)
        idatas = self.get_pending_invoice(customer, session_id)
        inv_lines = {}
        for idata in idatas:
            lines = self.fetch_invoice_lines(idata['id'])
            inv_lines[idata['id']] = lines
        result = {'orders': datas, 'pendinginvoice': idatas, 'inv_lines': inv_lines}
        return result


    #   Serialize all orders of the devotee -- rows - list of orders
    @api.model
    def get_order_datas(self, rows, session_id):
        """ Serialize all orders of the devotee

        params: rows - list of orders
        """
        datas = []
        s_no = 0
        pos_ids = [x['order_id'] for x in rows if x['type'] == "POS"]
        p_orders = self.env['pos.order'].search([('id', 'in', pos_ids)])
        all_orders = {'POS': p_orders}
        for key, orders in all_orders.items():
            for order in orders:
                s_no = s_no + 1
                date_order = False
                invoices = self.env['account.move'].search([
                    ('id', 'in', order.account_move.ids)])
                date_order = fields.Date.from_string(order.date_order)
                session_id = order.session_id.id
                if date_order:
                    date_order = date_order.strftime("%Y/%m/%d")
                else:
                    date_order = ''
                if invoices:
                    for invoice in invoices:
                        datas.append({
                            'id': order.id,
                            'sno': s_no,
                            'type': key,
                            'invoice_ref': invoice.name,
                            'invoice_id': invoice.id,
                            'amount_total': round(order.amount_total, 2),
                            'date_order': date_order,
                            'name': order.name or '',
                            'session_id': session_id})
                else:
                    datas.append({'id': order.id,
                                  'sno': s_no,
                                  'type': key,
                                  'invoice_ref': '',
                                  'invoice_id': '',
                                  'amount_total': round(order.amount_total, 2),
                                  'date_order': date_order,
                                  'name': order.name or '',
                                  'session_id': session_id})
        return datas


    #   Fetch the pending invoice for current user
    @api.model
    def get_pending_invoice(self, partner_id, session_id):
        """ Fetch the pending invoice for current user
        params: partner - current user
        """
        idatas = []

        p_invoice = self.env['account.move'].search(
            [('partner_id', '=', partner_id),
             ('move_type', 'not in', ('in_invoice', 'in_refund')),
             ('state', '=', 'posted'),
             ('payment_state', '!=', 'paid')])
        i_sno = 0
        paid_amount = 0
        for invoice in p_invoice:
            i_sno = i_sno + 1
            pos_order = self.env['pos.order'].search([
                ('account_move', '=', invoice.id)])
            type = 'POS'
            paid_amount1 = 0
            if pos_order:
                if pos_order.payment_ids:
                    paid_amount1 = sum(
                        [x.amount for x in pos_order.payment_ids if not x.payment_method_id.split_transactions])
                paid_amount = paid_amount1
                # To avoid return orders in pending invoice
                if (paid_amount < 0):
                    paid_amount = -(paid_amount)
                date_invoice = fields.Date.from_string(invoice.invoice_date)
                diff = (invoice.amount_total - paid_amount)
                amt = round(diff, 2)
                if diff == 0:
                    amt = 0
                pos_session = self.env['pos.session'].sudo().search([
                    ('state', '=', 'opened'), ('user_id', '=', self.env.uid)], limit=1)
                idatas.append({'id': invoice.id,
                               'sno': i_sno,
                               'type': type,
                               'porder_id': pos_order.id or '',
                               'session_name': pos_session.name,
                               'pos_session_name': pos_order.session_id.name,
                               'name': invoice.invoice_origin or '',
                               'invoice_ref': invoice.name,
                               'amount_total': round(invoice.amount_total, 2),
                               'unpaid_amount': amt if amt > 0 else '',
                               'date_invoice': date_invoice.strftime("%Y/%m/%d")
                               })

        return idatas

    @api.model
    def fetch_invoice_lines(self, invoice_id):
        """ Serialize the invoice Lines
        params: devotee int representing the invoice id
        """
        invoice = self.env['account.move'].browse(int(invoice_id))
        i_Lines = invoice.invoice_line_ids
        line = []
        s_no = 0
        for iLine in i_Lines:
            s_no = s_no + 1
            line.append({
                'sno': s_no,
                'id': iLine.id,
                'product': iLine.product_id.name,
                'qty': iLine.quantity,
                'price_unit': iLine.price_unit,
                'amount': iLine.price_subtotal
            })
        return line

    def _generate_pos_order_invoice(self):
        super(PosOrder, self)._generate_pos_order_invoice()
        moves = self.env['account.move']

        for order in self:
            # Force company for all SUPERUSER_ID action
            if order.account_move:
                moves += order.account_move
                continue

            if not order.partner_id:
                raise UserError(_('Please provide a partner for the sale.'))

            move_vals = order._prepare_invoice_vals()
            new_move = order._create_invoice(move_vals)

            order.write({'account_move': new_move.id, 'state': 'invoiced'})
            new_move.sudo().with_company(order.company_id).with_context(skip_invoice_sync=True)._post()

            moves += new_move
            for payment in order.payment_ids:
                if not payment.payment_method_id.split_transactions:
                    payment_moves = order._apply_invoice_payments(order.session_id.state == 'closed')
            for move_line in order.account_move.line_ids.filtered(lambda aml: aml.account_id.internal_type == 'receivable'):
                paylater_amt = 0.0
                for payment in order.payment_ids:
                    if payment.payment_method_id.split_transactions:
                        move_line.write({'is_pay_later': True})
                        paylater_amt += payment.amount
                    move_line.write({'paylater_amt': paylater_amt})

            # Send and Print
            if self.env.context.get('generate_pdf', True):
                template = self.env.ref(new_move._get_mail_template())
                new_move.with_context(skip_invoice_sync=True)._generate_pdf_and_send_invoice(template)


            if order.session_id.state == 'closed':  # If the session isn't closed this isn't needed.
                # If a client requires the invoice later, we need to revers the amount from the closing entry, by making a new entry for that.
                order._create_misc_reversal_move(payment_moves)

        if not moves:
            return {}

        return {
            'name': _('Customer Invoice'),
            'view_mode': 'form',
            'view_id': self.env.ref('account.view_move_form').id,
            'res_model': 'account.move',
            'context': "{'move_type':'out_invoice'}",
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': moves and moves.ids[0] or False,
        }

    def action_pos_order_paid(self):
        self.ensure_one()

        # TODO: add support for mix of cash and non-cash payments when both cash_rounding and only_round_cash_method are True
        if not self.config_id.cash_rounding \
           or self.config_id.only_round_cash_method \
           and not any(p.payment_method_id.is_cash_count for p in self.payment_ids):
            total = self.amount_total
        else:
            total = float_round(self.amount_total, precision_rounding=self.config_id.rounding_method.rounding, rounding_method=self.config_id.rounding_method.rounding_method)

        isPaid = float_is_zero(total - self.amount_paid, precision_rounding=self.currency_id.rounding)

        if not self.is_pay_later and not isPaid and not self.config_id.cash_rounding:
            raise UserError(_("Order %s is not fully paid.", self.name))
        elif not isPaid and self.config_id.cash_rounding:
            currency = self.currency_id
            if self.config_id.rounding_method.rounding_method == "HALF-UP":
                maxDiff = currency.round(self.config_id.rounding_method.rounding / 2)
            else:
                maxDiff = currency.round(self.config_id.rounding_method.rounding)

            diff = currency.round(self.amount_total - self.amount_paid)
            if not abs(diff) <= maxDiff:
                raise UserError(_("Order %s is not fully paid.", self.name))

        self.write({'state': 'paid'})

        return True
