from odoo.tests.common import TransactionCase, new_test_user
from odoo.exceptions import AccessError, ValidationError
from odoo import fields
from unittest.mock import patch, Mock
import base64
import io
import json
import openpyxl
from ..models.features import KINDS, PRESETS, date_range


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

    def _dataset_item(self, kind='bar'):
        dataset = self.env['tecnodyne.dashboard.dataset'].create({'name': 'Test source', 'row_ids': [
            (0, 0, {'name': 'Alpha', 'category': 'A', 'value': 10, 'value2': 3, 'date': '2026-01-01', 'latitude': 14.6, 'longitude': -90.5}),
            (0, 0, {'name': 'Beta', 'category': 'B', 'value': 20, 'value2': 5, 'date': '2026-01-03', 'latitude': 15, 'longitude': -91}),
        ]})
        model = 'tecnodyne.dashboard.dataset.row'
        def field(name):
            return self.env['ir.model.fields']._get(model, name).id
        return self.env['tecnodyne.dashboard.item'].create({
            'name': kind, 'dashboard_id': self.board.id, 'kind': kind,
            'model_id': self.env['ir.model']._get_id(model), 'aggregation': 'sum',
            'measure_id': field('value'), 'measure2_id': field('value2'),
            'group_field_id': field('category'), 'date_field_id': field('date'),
            'latitude_id': field('latitude'), 'longitude_id': field('longitude'),
            'domain_json': json.dumps([['dataset_id', '=', dataset.id]]),
        })

    def test_all_visualization_payloads(self):
        item = self._dataset_item()
        for kind in ['kpi', 'bar', 'line', 'pie', 'table'] + [k for k, label in KINDS]:
            item.kind = kind
            data = item.with_user(self.viewer)._payload()
            self.assertEqual(data['kind'], kind)
            if kind == 'kpi':
                self.assertEqual(data['value'], 30)
            elif kind != 'todo':
                self.assertEqual(len(data['rows']), 2)

    def test_item_audience_is_enforced(self):
        self.item.group_ids = self.env.ref('base.group_system')
        self.assertEqual(self.board.with_user(self.viewer).get_dashboard()['items'], [])
        with self.assertRaises(AccessError):
            self.item.with_user(self.viewer).get_item()

    def test_personal_layouts_are_private(self):
        board = self.board.with_user(self.viewer)
        board.save_named_layout('My layout', {str(self.item.id): {'order': 1, 'width': 2, 'height': 500}})
        self.assertEqual(board.select_named_layout('My layout')[str(self.item.id)]['width'], 2)
        prefs = self.env['tecnodyne.dashboard.preference'].search([('user_id', '=', self.viewer.id)])
        with self.assertRaises(AccessError):
            prefs.with_user(self.viewer).write({'user_id': self.env.ref('base.user_admin').id})

    def test_all_date_presets(self):
        today = fields.Date.to_date('2026-11-02')
        for key, label in PRESETS:
            start, end = date_range(key, today)
            if start:
                self.assertLessEqual(start, end)
        self.assertEqual(date_range('last_7', today), (fields.Date.to_date('2026-10-27'), today))

    def test_named_filter_and_subgroup(self):
        item = self._dataset_item()
        filter = self.env['tecnodyne.dashboard.filter'].create({'name': 'A', 'dashboard_id': self.board.id, 'model_id': item.model_id.id, 'domain_json': '[["category", "=", "A"]]'})
        item.subgroup_id = self.env['ir.model.fields']._get(item.model_name, 'name')
        data = item.with_user(self.viewer).with_context(td_filters=[filter.id])._payload()
        self.assertEqual(len(data['rows']), 1)
        self.assertEqual(data['rows'][0]['series'], 'Alpha')

    def test_drill_hierarchy_and_invalid_path(self):
        item = self._dataset_item()
        item.drill_field_ids = self.env['ir.model.fields']._get(item.model_name, 'name')
        data = item.with_user(self.viewer).get_item(path=[0])
        self.assertEqual(data['level'], 1)
        self.assertEqual(data['rows'][0]['label'], 'Alpha')
        with self.assertRaises(ValidationError):
            item.with_user(self.viewer).get_item(path=[500])

    def test_export_complete_and_formula_safe(self):
        item = self._dataset_item('list')
        item.limit = 1
        item.list_field_ids = self.env['ir.model.fields']._get(item.model_name, 'name')
        rows = self.env[item.model_name].search([('dataset_id', '=', json.loads(item.domain_json)[0][2])])
        rows[0].name = '=1+2'
        result = item.with_user(self.viewer).export_file('xlsx')
        book = openpyxl.load_workbook(io.BytesIO(base64.b64decode(result['content'])))
        self.assertEqual(book.active.max_row, 3)
        self.assertEqual(book.active['A2'].data_type, 's')
        self.assertIn("'=1+2", base64.b64decode(item.export_file('csv')['content']).decode())

    def test_csv_import_and_replace(self):
        wizard = self.env['tecnodyne.dashboard.import'].create({'name': 'CSV', 'dashboard_id': self.board.id, 'filename': 'data.csv', 'file': base64.b64encode(b'name,category,value\nOne,Test,12\n')})
        wizard.action_import()
        item = self.board.item_ids.filtered(lambda i: i.name == 'CSV')
        self.assertEqual(item._payload()['rows'][0]['value'], 12)
        dataset = self.env[item.model_name].search(json.loads(item.domain_json)).mapped('dataset_id')
        wizard.dataset_id = dataset
        wizard.file = base64.b64encode(b'name,category,value\nTwo,Test,99\n')
        wizard.action_import()
        self.assertEqual(item._payload()['rows'][0]['value'], 99)

    def test_tasks_and_chat_for_viewer(self):
        self.item.kind = 'todo'
        task = self.env['tecnodyne.dashboard.task'].create({'name': 'Review inventory', 'item_id': self.item.id})
        task.with_user(self.viewer).write({'done': True})
        self.assertTrue(task.done)
        with self.assertRaises(AccessError):
            task.with_user(self.viewer).write({'name': 'Change'})
        message = self.item.with_user(self.viewer).message_post(body='Internal dashboard discussion', message_type='comment', subtype_xmlid='mail.mt_comment')
        self.assertEqual(message.model, self.item._name)

    def test_ai_contract_and_review(self):
        self.env['ir.config_parameter'].sudo().set_param('tecnodyne_dashboard.ollama_url', 'http://127.0.0.1:11434')
        self.env['ir.config_parameter'].sudo().set_param('tecnodyne_dashboard.ollama_model', 'test-model')
        proposal = json.dumps({'items': [{'name': 'AI count', 'kind': 'kpi', 'aggregation': 'count', 'domain': []}]})
        response = Mock()
        response.json.return_value = {'response': proposal}
        with patch('odoo.addons.tecnodyne_dashboard.models.features.requests.post', return_value=response) as request:
            wizard = self.env['tecnodyne.dashboard.generate'].create({'name': 'AI', 'model_id': self.item.model_id.id, 'keywords': 'Count contacts', 'dashboard_id': self.board.id})
            wizard.action_generate()
            self.assertNotIn('TD A', request.call_args.kwargs['json']['prompt'])
            wizard.action_apply()
        self.assertTrue(self.board.item_ids.filtered(lambda i: i.name == 'AI count'))

    def test_realtime_event_has_no_business_values(self):
        item = self._dataset_item()
        with patch.object(type(self.env['bus.bus']), '_sendone') as notify:
            self.env[item.model_name].create({'dataset_id': json.loads(item.domain_json)[0][2], 'name': 'Confidential', 'value': 999})
            self.assertTrue(any(call.args[-1] == {'model': item.model_name} for call in notify.call_args_list))
            self.assertNotIn('Confidential', str(notify.call_args_list))

    def test_pdf_html_is_renderable(self):
        html, kind = self.env['ir.actions.report']._render_qweb_html('tecnodyne_dashboard.dashboard_pdf', self.item.ids)
        self.assertIn(b'TECNODYNE', html)

    def test_comparison_and_gap_filling(self):
        item = self._dataset_item('kpi')
        item.comparison = 'previous'
        data = item._payload('2026-01-03', '2026-01-04')
        self.assertEqual(data['value'], 20)
        self.assertEqual(data['previous'], 10)
        self.assertEqual(data['change'], 100)
        item.write({'kind': 'line', 'comparison': 'none', 'group_field_id': item.date_field_id.id,
                    'interval': 'day', 'fill_gaps': True, 'cumulative': True})
        data = item._payload()
        self.assertEqual([row['value'] for row in data['rows']], [10, 10, 30])

    def test_currency_conversion_precedes_aggregation(self):
        item = self._dataset_item('kpi')
        usd = self.env.ref('base.USD')
        eur = self.env.ref('base.EUR')
        self.a.currency_id = usd
        self.env['res.currency.rate'].create({'name': '2026-01-01', 'currency_id': usd.id, 'company_id': self.a.id, 'rate': 1})
        self.env['res.currency.rate'].create({'name': '2026-01-01', 'currency_id': eur.id, 'company_id': self.a.id, 'rate': 0.5})
        records = self.env[item.model_name].search(json.loads(item.domain_json))
        records[0].write({'amount': 10, 'currency_id': usd.id})
        records[1].write({'amount': 10, 'currency_id': eur.id})
        item.write({'measure_id': self.env['ir.model.fields']._get(item.model_name, 'amount').id, 'currency_id': usd.id})
        self.assertEqual(item._payload()['value'], 30)

    def test_kpi_formula_and_cycle_detection(self):
        item = self._dataset_item('kpi')
        item.kpi_operation = 'percentage'
        self.assertEqual(item._payload()['value'], 375)
        self.assertEqual(item._payload()['unit'], '%')
        with self.assertRaises(ValidationError), self.cr.savepoint():
            item.comparison_item_id = item

    def test_pagination_keeps_record_domain(self):
        item = self._dataset_item('list')
        item.limit = 1
        page = item.get_page(page=1)
        action = item.action_drill(row_index=0, page=1)
        self.assertEqual(self.env[item.model_name].search(action['domain']).id, page['rows'][0]['id'])

    def test_additional_measures_are_exported(self):
        item = self._dataset_item()
        field = self.env['ir.model.fields']._get(item.model_name, 'latitude')
        item.extra_measure_ids = field
        self.assertEqual(item._payload()['rows'][0]['measures']['latitude'], 14.6)
        result = item.export_file('xlsx')
        book = openpyxl.load_workbook(io.BytesIO(base64.b64decode(result['content'])))
        self.assertIn('Latitude', [cell.value for cell in book.active[1]])

    def test_private_discuss_channel(self):
        action = self.item.with_user(self.viewer).action_conversation()
        self.assertIn('/odoo/discuss', action['url'])
        channel = self.env['discuss.channel'].search([('td_item_id', '=', self.item.id)])
        self.assertTrue(channel.with_user(self.viewer).has_access('read'))
        self.item.group_ids = self.env.ref('base.group_system')
        self.assertFalse(channel.with_user(self.viewer).has_access('read'))

    def test_portable_dataset_and_kpi_queries(self):
        item = self._dataset_item('kpi')
        second = item.copy({'name': 'Secondary', 'measure2_id': False})
        item.write({'comparison_item_id': second.id, 'kpi_operation': 'ratio'})
        wizard = self.env['tecnodyne.dashboard.transfer'].create({'dashboard_id': self.board.id, 'item_id': item.id})
        wizard.action_export()
        action = wizard.action_import()
        board = self.env['tecnodyne.dashboard'].browse(action['params']['dashboard_id'])
        imported = board.item_ids.filtered(lambda i: i.name == item.name)
        self.assertTrue(imported.comparison_item_id)
        self.assertEqual(imported._payload()['value'], 1)

    def test_lmstudio_chat_and_structured_output(self):
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('tecnodyne_dashboard.lm_api', 'compat')
        params.set_param('tecnodyne_dashboard.ai_provider', 'lmstudio')
        params.set_param('tecnodyne_dashboard.ollama_url', 'http://127.0.0.1:1234/v1/')
        params.set_param('tecnodyne_dashboard.ollama_model', 'qwen3.5-4b')
        params.set_param('tecnodyne_dashboard.ai_key', 'test-token')
        response = Mock()
        response.json.return_value = {'choices': [{'message': {'content': '{"items":[]}'}, 'finish_reason': 'stop'}]}
        with patch('odoo.addons.tecnodyne_dashboard.models.features.requests.post', return_value=response) as request:
            result = self.env['tecnodyne.dashboard.ai']._generate('Generate JSON', json_mode=True)
            self.assertEqual(result, '{"items":[]}')
            self.assertEqual(request.call_args.args[0], 'http://127.0.0.1:1234/v1/chat/completions')
            self.assertEqual(request.call_args.kwargs['headers']['Authorization'], 'Bearer test-token')
            payload = request.call_args.kwargs['json']
            self.assertEqual(payload['response_format']['type'], 'json_schema')
            self.assertEqual(payload['messages'][-1]['content'], 'Generate JSON')
            self.assertNotIn('prompt', payload)

    def test_lmstudio_model_list_and_embedding_rejection(self):
        from odoo.exceptions import UserError
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('tecnodyne_dashboard.ai_provider', 'lmstudio')
        params.set_param('tecnodyne_dashboard.ollama_url', 'http://127.0.0.1:1234')
        params.set_param('tecnodyne_dashboard.ollama_model', 'qwen3.5-4b')
        response = Mock()
        response.json.return_value = {'data': [{'id': 'qwen3.5-4b'}]}
        with patch('odoo.addons.tecnodyne_dashboard.models.features.requests.get', return_value=response) as request:
            self.assertTrue(self.env['tecnodyne.dashboard.ai']._check_connection())
            self.assertEqual(request.call_args.args[0], 'http://127.0.0.1:1234/v1/models')
            params.set_param('tecnodyne_dashboard.ollama_model', 'missing-model')
            with self.assertRaises(UserError):
                self.env['tecnodyne.dashboard.ai']._check_connection()
            params.set_param('tecnodyne_dashboard.ollama_model', 'text-embedding-test')
            response.json.return_value = {'data': [{'id': 'text-embedding-test'}]}
            with self.assertRaises(UserError):
                self.env['tecnodyne.dashboard.ai']._check_connection()

    def test_lmstudio_rejects_truncated_generation(self):
        from odoo.exceptions import UserError
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('tecnodyne_dashboard.lm_api', 'compat')
        params.set_param('tecnodyne_dashboard.ai_provider', 'lmstudio')
        params.set_param('tecnodyne_dashboard.ollama_url', 'http://127.0.0.1:1234')
        params.set_param('tecnodyne_dashboard.ollama_model', 'qwen3.5-4b')
        response = Mock()
        response.json.return_value = {'choices': [{'message': {'content': '{"items":['}, 'finish_reason': 'length'}]}
        with patch('odoo.addons.tecnodyne_dashboard.models.features.requests.post', return_value=response):
            with self.assertRaises(UserError):
                self.env['tecnodyne.dashboard.ai']._generate('Generate JSON', json_mode=True)

    def test_lmstudio_native_ignores_reasoning_and_disables_storage(self):
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('tecnodyne_dashboard.ai_provider', 'lmstudio')
        params.set_param('tecnodyne_dashboard.lm_api', 'native')
        params.set_param('tecnodyne_dashboard.ollama_url', 'http://127.0.0.1:1234/v1')
        params.set_param('tecnodyne_dashboard.ollama_model', 'qwen3.5-4b')
        response = Mock()
        response.json.return_value = {'output': [{'type': 'reasoning', 'content': 'Not a final answer'},
                                                {'type': 'message', 'content': '```json\n{"items":[]}\n```'}]}
        with patch('odoo.addons.tecnodyne_dashboard.models.features.requests.post', return_value=response) as request:
            self.assertEqual(self.env['tecnodyne.dashboard.ai']._generate('JSON', json_mode=True), '{"items":[]}')
            self.assertEqual(request.call_args.args[0], 'http://127.0.0.1:1234/api/v1/chat')
            self.assertEqual(request.call_args.kwargs['json']['reasoning'], 'off')
            self.assertFalse(request.call_args.kwargs['json']['store'])
            response.json.return_value = {'output': [{'type': 'message', 'content': '{"items":[]}`'}]}
            self.assertEqual(self.env['tecnodyne.dashboard.ai']._generate('JSON', json_mode=True), '{"items":[]}')
            response.json.return_value = {'output': [{'type': 'message', 'content': '<think>not a proposal</think>\n{"items":[]}`'}]}
            self.assertEqual(self.env['tecnodyne.dashboard.ai']._generate('JSON', json_mode=True), '{"items":[]}')
            response.json.return_value = {'output': [{'type': 'reasoning', 'content': '{"items":[]}'}]}
            from odoo.exceptions import UserError
            with self.assertRaisesRegex(UserError, 'no final answer'):
                self.env['tecnodyne.dashboard.ai']._generate('JSON', json_mode=True)

    def test_ai_timeout_is_not_reported_as_connection_failure(self):
        import requests
        from odoo.exceptions import UserError
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('tecnodyne_dashboard.ollama_url', 'http://127.0.0.1:1234/v1')
        params.set_param('tecnodyne_dashboard.ollama_model', 'qwen3.5-4b')
        with patch('odoo.addons.tecnodyne_dashboard.models.features.requests.post', side_effect=requests.ReadTimeout()):
            with self.assertRaisesRegex(UserError, '180-second'):
                self.env['tecnodyne.dashboard.ai']._generate('JSON', json_mode=True)

    def test_ai_proposal_rejects_wrong_field_types_before_apply(self):
        wizard = self.env['tecnodyne.dashboard.generate'].create({'name': 'Test', 'model_id': self.item.model_id.id, 'keywords': 'Test'})
        raw = json.dumps({'items': [{'name': 'Bad sum', 'kind': 'kpi', 'aggregation': 'sum', 'measure': 'name'}]})
        with self.assertRaises(ValidationError):
            wizard._validated_items(raw)
