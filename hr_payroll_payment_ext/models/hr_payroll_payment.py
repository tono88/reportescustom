# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

def _resolve_employee_partner(employee):
    """Return the best partner to pay the employee, compatible with Odoo 17/18 field names."""
    # Try common fields in order of preference
    field_candidates = ['address_home_id', 'private_address_id', 'work_contact_id', 'user_partner_id', 'address_id']
    for fname in field_candidates:
        if fname in employee._fields:
            partner = employee[fname]
            if partner:
                return partner
    return False

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
        partner = _resolve_employee_partner(employee)
        if not partner:
            raise UserError(_("Employee %s has no payable Partner (private/work contact) set.") % employee.name)
        return partner

    def _get_slip_net_amount(self, slip):
        net_line = slip.line_ids.filtered(lambda l: l.code and l.code.upper() in ('NET', 'NETO'))
        if net_line:
            return net_line[0].total
        total = sum(slip.line_ids.filtered(lambda l: l.category_id and l.category_id.code in ('BASIC','ALW','ALWANCE','GROSS')).mapped('total'))                 - sum(slip.line_ids.filtered(lambda l: l.category_id and l.category_id.code in ('DED','DEDUCTION')).mapped('total'))
        return total

    def _pick_payment_method_line(self, journal, prefer_check=False):
        method_lines = journal.outbound_payment_method_line_ids
        if not method_lines:
            raise UserError(_("Journal %s has no outbound payment methods configured.") % journal.display_name)
        if prefer_check:
            def is_check(ml):
                name = (ml.name or '').lower()
                pm = ml.payment_method_id
                return ('check' in name) or (pm and ((pm.code in ('check_printing', 'check')) or ('check' in (pm.name or '').lower())))
            check_ml = method_lines.filtered(is_check)
            if not check_ml:
                raise UserError(_("The selected journal has no 'Check' outbound payment method.\n"
                                  "Add it in Accounting → Configuration → Journals → Payment Methods."))
            return check_ml[0]
        return method_lines[0]

    def _ensure_ready_to_pay(self):
        for run in self:
            if run.state != 'close':
                raise UserError(_("Close (post) the payroll batch before creating payments."))
            if not run.payment_journal_id:
                raise UserError(_("Select a Payment Journal."))

    def action_create_payments(self, prefer_check=False, auto_post=True):
        self._ensure_ready_to_pay()
        for run in self:
            journal = self.payment_journal_id
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
            slip.payment_id = payment.id
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


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    payment_id = fields.Many2one('account.payment', string="Payment", readonly=True)

    def _get_net_amount(self):
        self.ensure_one()
        net_line = self.line_ids.filtered(lambda l: l.code and l.code.upper() in ('NET', 'NETO'))
        if net_line:
            return net_line[0].total
        total = sum(self.line_ids.filtered(lambda l: l.category_id and l.category_id.code in ('BASIC','ALW','ALWANCE','GROSS')).mapped('total'))                 - sum(self.line_ids.filtered(lambda l: l.category_id and l.category_id.code in ('DED','DEDUCTION')).mapped('total'))
        return total

    def _ensure_ready_to_pay_single(self):
        self.ensure_one()
        if self.state != 'done' and (self.payslip_run_id and self.payslip_run_id.state != 'close'):
            raise UserError(_("Confirm the payslip (Done) or close its batch before creating payments."))
        run = self.payslip_run_id
        if not run or not run.payment_journal_id:
            raise UserError(_("Select a Payment Journal on the batch (Procesamientos de nóminas)."))
        return run

    def _get_employee_partner(self):
        partner = _resolve_employee_partner(self.employee_id)
        if not partner:
            raise UserError(_("Employee %s has no payable Partner (private/work contact) set.") % self.employee_id.name)
        return partner

    def action_create_payment(self, prefer_check=False, auto_post=True):
        self.ensure_one()
        run = self._ensure_ready_to_pay_single()
        journal = run.payment_journal_id
        method_line = run._pick_payment_method_line(journal, prefer_check=prefer_check)
        amount = self._get_net_amount()
        if not amount:
            raise UserError(_("No amount found on this payslip."))
        partner = self._get_employee_partner()
        vals = {
            'date': run.payment_date or fields.Date.context_today(self),
            'journal_id': journal.id,
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': partner.id,
            'amount': abs(amount),
            'currency_id': self.company_id.currency_id.id,
            'payment_method_line_id': method_line.id,
            'ref': _("Payroll %s - %s") % (run.name or self.name, self.employee_id.name),
        }
        payment = self.env['account.payment'].create(vals)
        if auto_post:
            payment.action_post()
        self.payment_id = payment.id
        if run:
            run.payment_ids = [(4, payment.id)]
        return True

    def action_create_check_payment(self):
        """Create a CHECK payment for this payslip."""
        return self.action_create_payment(prefer_check=True, auto_post=True)

    def action_view_payment(self):
        self.ensure_one()
        action = self.env.ref('account.action_account_payments').read()[0]
        action['domain'] = [('id', 'in', [self.payment_id.id])]
        action['context'] = {'default_journal_id': self.payslip_run_id.payment_journal_id.id if self.payslip_run_id else False}
        return action
