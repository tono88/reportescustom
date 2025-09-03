# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class HrPayslipRun(models.Model):
    _inherit = "hr.payslip.run"

    payment_state = fields.Selection([
        ('none', 'No Payment'),
        ('to_pay', 'To Pay'),
        ('paid', 'Paid'),
    ], string="Payment State", default='none')
    payment_journal_id = fields.Many2one(
        'account.journal',
        string="Payment Journal",
        domain="[('type', 'in', ('bank','cash'))]"
    )
    payment_date = fields.Date(string="Payment Date", default=fields.Date.context_today)
    payment_mode = fields.Selection([
        ('per_employee', 'Per employee (one payment each)'),
        ('batch', 'One payment for whole batch'),
    ], default='per_employee', string="Payment Mode", required=True)
    payment_ids = fields.Many2many('account.payment', string="Related Payments", readonly=True)
    payment_count = fields.Integer(compute="_compute_payment_count")

    @api.depends('payment_ids')
    def _compute_payment_count(self):
        for run in self:
            run.payment_count = len(run.payment_ids)

    def action_view_payments(self):
        self.ensure_one()
        action = self.env.ref('account.action_account_payments').read()[0]
        action['domain'] = [('id', 'in', self.payment_ids.ids)]
        action['context'] = {'default_journal_id': self.payment_journal_id.id}
        return action

    def _get_employee_partner(self, employee):
        partner = employee.address_home_id
        if not partner:
            raise UserError(_("Employee %s has no Private Address (home) partner set.") % employee.name)
        return partner

    def _get_slip_net_amount(self, slip):
        net_line = slip.line_ids.filtered(lambda l: l.code and l.code.upper() in ('NET', 'NETO'))
        if net_line:
            return net_line[0].total
        total = sum(slip.line_ids.filtered(lambda l: l.category_id and l.category_id.code in ('BASIC','ALW','ALWANCE','GROSS')).mapped('total')) \
                - sum(slip.line_ids.filtered(lambda l: l.category_id and l.category_id.code in ('DED','DEDUCTION')).mapped('total'))
        return total

    def _pick_payment_method_line(self, journal, prefer_check=False):
        method_lines = journal.outbound_payment_method_line_ids
        if not method_lines:
            raise UserError(_("Journal %s has no outbound payment methods configured.") % journal.display_name)
        if prefer_check:
            check_ml = method_lines.filtered(lambda m: 'check' in (m.name or '').lower())
            if check_ml:
                return check_ml[0]
        return method_lines[0]

    def _ensure_ready_to_pay(self):
        for run in self:
            # Accepted terminal states in 18.0 typically 'close' (posted) or 'verify' (awaiting)
            if run.state not in ('close', 'verify'):
                raise UserError(_("Confirm/Post the payroll batch before creating payments."))
            if not run.payment_journal_id:
                raise UserError(_("Select a Payment Journal."))

    def action_create_payments(self, prefer_check=False, auto_post=True):
        self._ensure_ready_to_pay()
        for run in self:
            journal = run.payment_journal_id
            method_line = self._pick_payment_method_line(journal, prefer_check=prefer_check)
            if run.payment_mode == 'per_employee':
                payments = self._create_payments_per_employee(run, journal, method_line, auto_post=auto_post)
                run.payment_ids = [(4, p.id) for p in payments]
            else:
                payment = self._create_one_payment_for_batch(run, journal, method_line, auto_post=auto_post)
                run.payment_ids = [(4, payment.id)]
            run.payment_state = 'to_pay' if not auto_post else 'paid'
        return True

    def _create_payments_per_employee(self, run, journal, method_line, auto_post=True):
        payments = self.env['account.payment']
        for slip in run.slip_ids:
            amount = self._get_slip_net_amount(slip)
            if not amount:
                continue
            employee = slip.employee_id
            partner = self._get_employee_partner(employee)
            vals = {
                'date': run.payment_date or fields.Date.context_today(self),
                'journal_id': journal.id,
                'payment_type': 'outbound',
                'partner_type': 'supplier',
                'partner_id': partner.id,
                'amount': abs(amount),
                'currency_id': run.company_id.currency_id.id,
                'payment_method_line_id': method_line.id,
                'ref': _("Payroll %s - %s") % (run.name, employee.name),
            }
            payment = self.env['account.payment'].create(vals)
            if auto_post:
                payment.action_post()
            payments += payment
        return payments

    def _create_one_payment_for_batch(self, run, journal, method_line, auto_post=True):
        total = 0.0
        for slip in run.slip_ids:
            total += (self._get_slip_net_amount(slip) or 0.0)
        if not total:
            raise UserError(_("No amount found on payslips."))
        clearing_partner = self.env['res.partner'].sudo().search([('name','=','Payroll Clearing'), ('company_id','in',[False, run.company_id.id])], limit=1)
        if not clearing_partner:
            clearing_partner = self.env['res.partner'].sudo().create({'name': 'Payroll Clearing', 'company_id': run.company_id.id})
        vals = {
            'date': run.payment_date or fields.Date.context_today(self),
            'journal_id': journal.id,
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': clearing_partner.id,
            'amount': abs(total),
            'currency_id': run.company_id.currency_id.id,
            'payment_method_line_id': method_line.id,
            'ref': _("Payroll %s - Batch Payment") % (run.name),
        }
        payment = self.env['account.payment'].create(vals)
        if auto_post:
            payment.action_post()
        return payment

    def action_mark_paid(self):
        self.write({'payment_state': 'paid'})
        return True