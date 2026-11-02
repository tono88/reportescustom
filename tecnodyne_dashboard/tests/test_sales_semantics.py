from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
import json


@tagged('post_install', '-at_install')
class TestSalesSemantics(TransactionCase):
    def test_cash_balance_includes_opening_history_and_empty_months(self):
        if 'account.move' not in self.env:
            self.skipTest('Install Accounting in the integration database.')
        company = self.env['res.company'].create({'name': 'Cash semantics QA', 'currency_id': self.env.company.currency_id.id})
        env = self.env(context=dict(self.env.context, allowed_company_ids=[company.id]))
        cash = env['account.account'].create({'name': 'Cash QA', 'code': 'QA100', 'account_type': 'asset_cash', 'company_ids': [(6, 0, [company.id])]})
        equity = env['account.account'].create({'name': 'Equity QA', 'code': 'QA300', 'account_type': 'equity', 'company_ids': [(6, 0, [company.id])]})
        journal = env['account.journal'].create({'name': 'Cash QA', 'code': 'QCASH', 'type': 'general', 'company_id': company.id})
        for day, amount, posted in [('2025-12-15', 100, True), ('2026-01-15', 20, True), ('2026-03-15', 30, True), ('2026-02-15', 999, False)]:
            move = env['account.move'].create({'journal_id': journal.id, 'date': day, 'line_ids': [
                (0, 0, {'name': 'Cash', 'account_id': cash.id, 'debit': amount}),
                (0, 0, {'name': 'Offset', 'account_id': equity.id, 'credit': amount})]})
            if posted:
                move.action_post()
        env.flush_all()
        for request, expected in [('Saldo de efectivo y bancos', [150]), ('Saldo de efectivo y bancos por mes', [120, 120, 150])]:
            wizard = env['tecnodyne.dashboard.generate'].create({'name': request, 'keywords': request, 'item_count': 1})
            wizard.action_generate()
            result = wizard.action_apply()
            item = env['tecnodyne.dashboard'].browse(result['params']['dashboard_id']).item_ids
            payload = item._payload('2026-01-01', '2026-03-31')
            values = [payload['value']] if item.kind == 'kpi' else [row['value'] for row in payload['rows']]
            self.assertEqual(values, expected)

    def test_sales_trend_is_monthly_sum_not_top_categories(self):
        if 'sale.report' not in self.env or 'report.pos.order' not in self.env:
            self.skipTest('Install Sales and POS in the integration database.')
        wizard = self.env['tecnodyne.dashboard.generate'].create({'keywords': 'Tendencia de ventas por mes en importe'})
        wizard.action_generate()
        for spec in json.loads(wizard.proposal)['items']:
            self.assertEqual(spec['group'], 'date')
            self.assertIsNone(spec['subgroup'])
            self.assertEqual(spec['top_n_per_period'], 0)
            self.assertEqual(spec['aggregation'], 'sum')

    def test_sales_request_resolves_transactional_sources_and_not_category_count(self):
        if 'sale.report' not in self.env or 'report.pos.order' not in self.env:
            self.skipTest('Install Sales and POS in the integration-test database.')
        wizard = self.env['tecnodyne.dashboard.generate'].create({'name': 'Categories by month',
            'model_id': self.env['ir.model']._get_id('product.category'), 'sales_channel': 'both', 'item_count': 8,
            'keywords': 'Quisiera un tablero con las categorías de productos más vendidas por mes'})
        wizard.action_generate()
        proposal = json.loads(wizard.proposal)
        self.assertEqual({item['model'] for item in proposal['items']}, {'sale.report', 'report.pos.order'})
        self.assertEqual({item['aggregation'] for item in proposal['items']}, {'sum'})
        self.assertEqual({item['subgroup'] for item in proposal['items']}, {'date'})
        self.assertEqual({item['interval'] for item in proposal['items']}, {'month'})
        self.assertEqual(wizard.proposal_engine, 'business')
        result = wizard.action_apply()
        board = self.env['tecnodyne.dashboard'].browse(result['params']['dashboard_id'])
        self.assertEqual(len(board.item_ids), 2)
        self.assertTrue(all(item.top_n_per_period == 10 for item in board.item_ids))
        bad = {'items': [{'name': 'Conteo de registros', 'kind': 'kpi', 'aggregation': 'count', 'domain': []}]}
        with self.assertRaises(ValidationError):
            wizard._validated_items(json.dumps(bad))

    def test_real_sales_excludes_quotes_and_cancelled_and_ranks_each_month(self):
        if 'sale.report' not in self.env or 'report.pos.order' not in self.env:
            self.skipTest('Install Sales and POS in the integration-test database.')
        category_a, category_b = self.env['product.category'].create([{'name': 'QA blocks'}, {'name': 'QA hardware'}])
        products = self.env['product.product'].create([{'name': 'Block', 'categ_id': category_a.id, 'list_price': 2},
                                                     {'name': 'Tool', 'categ_id': category_b.id, 'list_price': 3}])
        partner = self.env['res.partner'].create({'name': 'Sales QA customer'})
        for day, quantities, state in [('2026-01-12', (2, 8), 'sale'), ('2026-02-12', (9, 1), 'sale'), ('2026-01-15', (999, 0), 'draft'), ('2026-02-15', (999, 0), 'cancel')]:
            order = self.env['sale.order'].create({'partner_id': partner.id,
                'order_line': [(0, 0, {'product_id': product.id, 'product_uom_qty': quantity, 'price_unit': product.list_price}) for product, quantity in zip(products, quantities) if quantity]})
            if state == 'sale':
                order.action_confirm()
            elif state == 'cancel':
                order.action_cancel()
            order.date_order = day+' 12:00:00'
        self.env.flush_all()
        wizard = self.env['tecnodyne.dashboard.generate'].create({'name': 'Monthly rankings', 'sales_channel': 'sale', 'top_limit': 1,
            'keywords': 'Categorías más vendidas por mes', 'item_count': 1})
        result = wizard.action_generate()
        action = wizard.action_apply()
        item = self.env['tecnodyne.dashboard'].browse(action['params']['dashboard_id']).item_ids
        item.domain_json = json.dumps(json.loads(item.domain_json)+[['categ_id', 'in', [category_a.id, category_b.id]]])
        rows = item._payload('2026-01-01', '2026-02-28')['rows']
        self.assertEqual([(row['label'], row['value']) for row in rows], [(category_b.name, 8), (category_a.name, 9)])

    def test_real_pos_excludes_drafts_and_cancelled_per_month(self):
        if 'sale.report' not in self.env or 'report.pos.order' not in self.env:
            self.skipTest('Install Sales and POS in the integration-test database.')
        category_a, category_b = self.env['product.category'].create([{'name': 'POS blocks'}, {'name': 'POS hardware'}])
        products = self.env['product.product'].create([{'name': 'POS block', 'categ_id': category_a.id, 'list_price': 2},
                                                     {'name': 'POS tool', 'categ_id': category_b.id, 'list_price': 3}])
        journal = self.env['account.journal'].create({'name': 'QA POS journal', 'code': 'QPOS', 'type': 'general'})
        config = self.env['pos.config'].create({'name': 'QA semantic POS', 'journal_id': journal.id})
        session = self.env['pos.session'].create({'config_id': config.id})
        for day, quantities, state in [('2026-01-12', (3, 7), 'paid'), ('2026-02-12', (11, 5), 'done'), ('2026-01-15', (999, 0), 'draft'), ('2026-02-15', (999, 0), 'cancel')]:
            total = sum(product.list_price*quantity for product, quantity in zip(products, quantities))
            self.env['pos.order'].create({'session_id': session.id, 'company_id': self.env.company.id,
                'date_order': day+' 12:00:00', 'state': state, 'amount_tax': 0, 'amount_total': total,
                'amount_paid': total if state in ('paid', 'done') else 0, 'amount_return': 0,
                'lines': [(0, 0, {'name': product.name, 'product_id': product.id, 'qty': quantity,
                    'price_unit': product.list_price, 'price_subtotal': quantity*product.list_price,
                    'price_subtotal_incl': quantity*product.list_price}) for product, quantity in zip(products, quantities) if quantity]})
        self.env.flush_all()
        wizard = self.env['tecnodyne.dashboard.generate'].create({'name': 'POS monthly rankings', 'sales_channel': 'pos', 'top_limit': 1,
            'keywords': 'Categorías más vendidas por mes', 'item_count': 1})
        wizard.action_generate()
        action = wizard.action_apply()
        item = self.env['tecnodyne.dashboard'].browse(action['params']['dashboard_id']).item_ids
        item.domain_json = json.dumps(json.loads(item.domain_json)+[['product_categ_id', 'in', [category_a.id, category_b.id]]])
        rows = item._payload('2026-01-01', '2026-02-28')['rows']
        self.assertEqual([(row['label'], row['value']) for row in rows], [(category_b.name, 7), (category_a.name, 11)])
