from odoo.tests.common import TransactionCase, new_test_user
from odoo.exceptions import AccessError, ValidationError


class TestDashboard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.a = cls.env.company
        cls.b = cls.env['res.company'].create({'name': 'Tecnodyne isolated B'})
        cls.viewer = new_test_user(cls.env, login='td_viewer', groups='tecnodyne_dashboard.group_dashboard_user',
                                   company_id=cls.a.id, company_ids=[(6, 0, [cls.a.id])])
        cls.env['res.partner'].create([{'name': 'TD A', 'company_id': cls.a.id, 'ref': 'td_test'},
                                       {'name': 'TD B', 'company_id': cls.b.id, 'ref': 'td_test'}])
        cls.board = cls.env['tecnodyne.dashboard'].create({'name': 'Test', 'company_id': cls.a.id})
        cls.item = cls.env['tecnodyne.dashboard.item'].create({
            'name': 'Contacts', 'dashboard_id': cls.board.id,
            'model_id': cls.env['ir.model']._get_id('res.partner'),
            'domain_json': '[["ref", "=", "td_test"]]',
        })

    def test_company_count_and_drill(self):
        item = self.item.with_user(self.viewer)
        self.assertEqual(item._payload()['value'], 1)
        action = item.action_drill()
        self.assertEqual(self.env['res.partner'].with_user(self.viewer).search_count(action['domain']), 1)

    def test_other_company_denied(self):
        self.board.company_id = self.b
        with self.assertRaises(AccessError):
            self.board.with_user(self.viewer).get_dashboard()

    def test_viewer_cannot_edit(self):
        with self.assertRaises(AccessError):
            self.item.with_user(self.viewer).write({'name': 'Unauthorized'})

    def test_source_acl_preserved(self):
        self.item.model_id = self.env['ir.model']._get_id('ir.config_parameter')
        self.item.domain_json = '[]'
        with self.assertRaises(AccessError):
            self.board.with_user(self.viewer).get_dashboard()

    def test_audience_denied(self):
        self.board.group_ids = self.env.ref('base.group_system')
        with self.assertRaises(AccessError):
            self.board.with_user(self.viewer).get_dashboard()

    def test_grouped_count(self):
        self.item.write({'kind': 'table', 'group_field_id': self.env['ir.model.fields']._get('res.partner', 'company_id').id})
        rows = self.item.with_user(self.viewer)._payload()['rows']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['value'], 1)

    def test_domain_is_data(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.item.domain_json = "__import__('os').system('anything')"

    def test_transfer_roundtrip(self):
        wizard = self.env['tecnodyne.dashboard.transfer'].create({'dashboard_id': self.board.id})
        wizard.action_export()
        action = wizard.action_import()
        copy = self.env['tecnodyne.dashboard'].browse(action['params']['dashboard_id'])
        self.assertNotEqual(copy, self.board)
        self.assertEqual(copy.item_ids._payload()['value'], 1)

    def test_datetime_range_uses_user_timezone(self):
        self.item.date_field_id = self.env['ir.model.fields']._get('res.partner', 'create_date')
        target, domain = self.item.with_context(tz='America/Guatemala')._query('2026-01-01', '2026-01-01')
        self.assertIn(('create_date', '>=', '2026-01-01 06:00:00'), domain)
        self.assertIn(('create_date', '<', '2026-01-02 06:00:00'), domain)
