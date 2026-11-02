import json
from odoo.tests.common import TransactionCase, new_test_user
from odoo.exceptions import AccessError, ValidationError


class TestSnapshotQuery(TransactionCase):
    def setUp(self):
        super().setUp()
        self.board = self.env['tecnodyne.dashboard'].create({'name': 'SQL QA'})
        self.dataset = self.env['tecnodyne.dashboard.dataset'].create({'name': 'SQL source', 'row_ids': [
            (0, 0, {'name': 'One', 'category': 'A', 'value': 10}),
            (0, 0, {'name': 'Two', 'category': 'B', 'value': 20}),
        ]})
        model = 'tecnodyne.dashboard.dataset.row'
        self.item = self.env['tecnodyne.dashboard.item'].create({'name': 'SQL', 'dashboard_id': self.board.id,
            'model_id': self.env['ir.model']._get_id(model), 'kind': 'table', 'query_mode': 'sql',
            'query_sql': 'SELECT category AS label, SUM(value) AS value FROM source GROUP BY category',
            'query_source_ids': [(0, 0, {'alias': 'source', 'model_id': self.env['ir.model']._get_id(model),
                'field_ids': [(6, 0, self.env['ir.model.fields'].search([('model', '=', model), ('name', 'in', ['name', 'category', 'value', 'company_id'])]).ids)],
                'domain_json': json.dumps([['dataset_id', '=', self.dataset.id]])})]})

    def test_sql_aggregates_and_exports(self):
        data = self.item._payload()
        self.assertEqual([(row['label'], row['value']) for row in data['rows']], [('A', 10), ('B', 20)])
        self.assertTrue(self.item.export_file('xlsx')['content'])

    def test_cte_window_and_json_file_columns(self):
        self.dataset.row_ids[0].raw_json = {'extra': 5}
        self.dataset.row_ids[1].raw_json = {'extra': 7}
        self.item.query_source_ids.field_ids |= self.env['ir.model.fields']._get('tecnodyne.dashboard.dataset.row', 'raw_json')
        self.item.query_sql = "WITH totals AS (SELECT category AS label, SUM(json_extract(raw_json,'$.extra')) AS amount FROM source GROUP BY category) SELECT label,SUM(amount) OVER (ORDER BY label) AS value FROM totals ORDER BY label"
        self.assertEqual([row['value'] for row in self.item._payload()['rows']], [5, 12])

    def test_sql_and_typed_data_survive_transfer(self):
        self.item.query_source_ids.write({'date_scope': 'as_of', 'include_shared': True})
        self.dataset.column_types = {'extra': 'integer'}
        self.dataset.row_ids[0].raw_json = {'extra': 5}
        wizard = self.env['tecnodyne.dashboard.transfer'].create({'dashboard_id': self.board.id})
        wizard.action_export()
        imported = wizard.action_import()
        item = self.env['tecnodyne.dashboard'].browse(imported['params']['dashboard_id']).item_ids
        self.assertEqual(item.query_source_ids.date_scope, 'as_of')
        self.assertTrue(item.query_source_ids.include_shared)
        self.assertEqual([row['value'] for row in item._payload()['rows']], [10, 20])

    def test_sql_can_join_authorized_sources(self):
        source = self.item.query_source_ids
        source.copy({'alias': 'other'})
        self.item.query_sql = 'SELECT a.category AS label, SUM(a.value+b.value) AS value FROM source a JOIN other b ON a.id=b.id GROUP BY a.category'
        self.assertEqual([row['value'] for row in self.item._payload()['rows']], [20, 40])

    def test_sql_cannot_bypass_company_or_record_acl(self):
        company = self.env['res.company'].create({'name': 'Other SQL company'})
        other = self.env['tecnodyne.dashboard.dataset'].create({'name': 'Hidden', 'company_id': company.id,
            'row_ids': [(0, 0, {'name': 'Secret', 'category': 'A', 'value': 999})]})
        self.item.query_source_ids.domain_json = json.dumps([['dataset_id', 'in', [self.dataset.id, other.id]]])
        user = new_test_user(self.env, login='td_sql_reader', groups='tecnodyne_dashboard.group_dashboard_user', company_id=self.env.company.id,
                             company_ids=[(6, 0, [self.env.company.id])])
        self.assertEqual(sum(row['value'] for row in self.item.with_user(user)._payload()['rows']), 30)
        source = self.item.query_source_ids
        source.write({'model_id': self.env['ir.model']._get_id('ir.config_parameter'),
                      'field_ids': [(6, 0, [self.env['ir.model.fields']._get('ir.config_parameter', 'key').id])], 'domain_json': '[]'})
        with self.assertRaises(AccessError):
            self.item.with_user(user)._payload()

    def test_sql_denies_external_tables_functions_and_writes(self):
        for query in ["SELECT name AS label, 1 AS value FROM sqlite_master", "SELECT load_extension('bad') AS label, 1 AS value", 'SELECT name AS label,value FROM source; DELETE FROM source']:
            self.item.query_sql = query
            with self.assertRaises(ValidationError):
                self.item._payload()
        self.assertEqual(len(self.dataset.row_ids), 2)

    def test_sql_uid_and_company_parameters(self):
        self.item.query_sql = 'SELECT name AS label, value FROM source WHERE company_id = %MYCOMPANY AND :uid > 0 ORDER BY value DESC'
        self.assertEqual([row['value'] for row in self.item._payload()['rows']], [20, 10])

    def test_sql_record_navigation_validates_source_id(self):
        self.item.query_sql = "SELECT name AS label, value, id AS record_id, 'source' AS source_alias FROM source ORDER BY id"
        action = self.item.action_drill(row_index=0)
        self.assertEqual(action['res_id'], self.dataset.row_ids.sorted('id')[0].id)
        self.item.query_sql = "SELECT name AS label, value, 999999 AS record_id, 'source' AS source_alias FROM source"
        with self.assertRaises(AccessError):
            self.item.action_drill(row_index=0)

    def test_recursive_sql_has_execution_budget(self):
        self.item.query_sql = 'WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM n) SELECT \'loop\' AS label, SUM(x) AS value FROM n'
        with self.assertRaises(ValidationError):
            self.item._payload()

    def test_sql_navigation_keeps_dashboard_filter(self):
        selected = self.env['tecnodyne.dashboard.filter'].create({'name': 'Only A', 'dashboard_id': self.board.id,
            'model_id': self.item.model_id.id, 'domain_json': '[["category","=","A"]]'})
        excluded = self.dataset.row_ids.filtered(lambda row: row.category == 'B')
        self.item.query_sql = "SELECT name AS label,value,%d AS record_id,'source' AS source_alias FROM source" % excluded.id
        with self.assertRaises(AccessError):
            self.item.action_drill(row_index=0, filter_ids=[selected.id])
