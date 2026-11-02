import json
from odoo import fields, models, _
from odoo.exceptions import ValidationError, UserError
from odoo.osv import expression


def remap_dataset_domain(raw, mapping):
    domain = json.loads(raw)
    for leaf in domain:
        if isinstance(leaf, list) and len(leaf) == 3 and leaf[0] == 'dataset_id':
            if leaf[1] == '=':
                leaf[2] = mapping[leaf[2]]
            elif leaf[1] in ('in', 'not in'):
                leaf[2] = [mapping[key] for key in leaf[2]]
            else:
                raise ValueError()
    return json.dumps(expression.AND([domain, [('dataset_id', 'in', list(mapping.values()))]]))


class Transfer(models.TransientModel):
    _name = 'tecnodyne.dashboard.transfer'
    _description = 'Dashboard JSON transfer'

    dashboard_id = fields.Many2one('tecnodyne.dashboard')
    item_id = fields.Many2one('tecnodyne.dashboard.item', domain="[('dashboard_id', '=', dashboard_id)]")
    import_into_dashboard = fields.Boolean(string='Import items into selected dashboard')
    document = fields.Text(string='JSON configuration')

    def action_export(self):
        self.ensure_one()
        board = self.dashboard_id
        if not board:
            raise ValidationError(_('Select a dashboard.'))
        board.check_access('read')
        items = []
        selected = self.item_id or board.item_ids
        # Keep independent KPI queries when exporting an individual indicator.
        pending = selected
        while pending:
            dependencies = pending.mapped('comparison_item_id') - selected
            selected |= dependencies
            pending = dependencies
        for item in selected:
            item.check_access('read')
            values = {key: item[key] for key in self._keys()}
            values['model'] = item.model_name
            for key in ('measure_id', 'group_field_id', 'date_field_id', 'measure2_id', 'subgroup_id', 'latitude_id', 'longitude_id'):
                values[key] = item[key].name or False
            values['list_fields'] = item.list_field_ids.mapped('name')
            values['drill_fields'] = item._drill_fields().mapped('name')
            values['extra_measures'] = item.extra_measure_ids.mapped('name')
            values['currency'] = item.currency_id.name or False
            values['key'] = str(item.id)
            values['comparison_key'] = str(item.comparison_item_id.id) if item.comparison_item_id else False
            values['tasks'] = [{'name': t.name, 'done': t.done} for t in item.task_ids]
            if item.client_action_id:
                xmlid = item.client_action_id.get_external_id().get(item.client_action_id.id)
                if not xmlid:
                    raise UserError(_('Assign an external ID to the custom action before exporting it.'))
                values['action_xmlid'] = xmlid
            values['targets'] = [{'date': str(t.date), 'value': t.value} for t in item.target_ids]
            values['query_sources'] = [{'alias': source.alias, 'model': source.model_name,
                'fields': source.field_ids.mapped('name'), 'date_field': source.date_field_id.name or False,
                'domain_json': source.domain_json, 'date_scope': source.date_scope,
                'include_shared': source.include_shared} for source in item.query_source_ids]
            items.append(values)
        filters = [{'name': f.name, 'model': f.model_id.model, 'domain_json': f.domain_json} for f in board.filter_ids]
        datasets = {}
        dataset_sources = self.env['tecnodyne.dashboard.dataset']
        for item in selected.filtered(lambda i: i.query_mode == 'orm' and i.model_name == 'tecnodyne.dashboard.dataset.row'):
            target, domain = item._query()
            rows = target.search(domain, limit=10001)
            if len(rows) > 10000:
                raise UserError(_('Narrow imported data to 10,000 rows before exporting.'))
            dataset_sources |= rows.mapped('dataset_id')
        for sql_source in selected.mapped('query_source_ids').filtered(lambda s: s.model_name == 'tecnodyne.dashboard.dataset.row'):
            columns, records, domain = sql_source._snapshot()
            target = self.env[sql_source.model_name].with_context(allowed_company_ids=[sql_source.item_id.company_id.id])
            dataset_sources |= target.search(domain, limit=10001).mapped('dataset_id')
        target = self.env['tecnodyne.dashboard.dataset.row'].with_context(allowed_company_ids=[board.company_id.id])
        for source in dataset_sources:
            dataset_rows = target.search([('dataset_id', '=', source.id)], limit=10001)
            if len(dataset_rows) > 10000:
                raise UserError(_('A dataset exceeds the 10,000 row transfer limit.'))
            datasets[str(source.id)] = {'name': source.name, 'column_types': source.column_types or {}, 'rows': [
                dict({key: row[key] for key in ('name', 'category', 'value', 'value2', 'amount', 'latitude', 'longitude', 'raw_json')},
                     date=str(row.date) if row.date else False, currency=row.currency_id.name)
                for row in dataset_rows]}
        self.document = json.dumps({'schema': 3, 'name': board.name, 'theme': board.theme, 'layout_template': board.layout_template, 'items': items, 'filters': filters, 'datasets': datasets}, ensure_ascii=False, indent=2)
        return self._reopen()

    def _keys(self):
        return ('name', 'sequence', 'kind', 'aggregation', 'interval', 'domain_json', 'limit', 'target', 'unit',
                'sort', 'preset', 'comparison', 'multiplier', 'cumulative', 'fill_gaps', 'stacked',
                'show_values', 'show_legend', 'number_format', 'icon', 'color',
                'secondary_as_line', 'cumulative_as_line', 'kpi_operation', 'target_style', 'tile_style', 'top_n_per_period', 'query_mode', 'query_sql', 'date_scope')

    def action_import(self):
        self.ensure_one()
        try:
            if len(self.document or '') > 10*1024*1024:
                raise ValueError()
            data = json.loads(self.document or '')
            if data['schema'] not in (1, 2, 3) or not isinstance(data['items'], list) or len(data['items']) > 100:
                raise ValueError()
            commands = []
            dataset_map = {}
            for old_id, source in data.get('datasets', {}).items():
                if len(source['rows']) > 10000:
                    raise ValueError()
                source_rows = []
                for row in source['rows']:
                    vals = {key: row.get(key) for key in ('name', 'category', 'value', 'value2', 'amount', 'latitude', 'longitude', 'date')}
                    vals['raw_json'] = row.get('raw_json') or {}
                    currency = self.env['res.currency'].search([('name', '=', row.get('currency'))], limit=1) if row.get('currency') else self.env.company.currency_id
                    if not currency:
                        raise ValueError()
                    vals['currency_id'] = currency.id
                    source_rows.append((0, 0, vals))
                dataset = self.env['tecnodyne.dashboard.dataset'].create({'name': source['name'], 'row_ids': source_rows, 'column_types': source.get('column_types') or {}})
                dataset_map[int(old_id)] = dataset.id
            for raw in data['items']:
                model = self.env['ir.model'].search([('model', '=', raw['model'])], limit=1)
                if not model:
                    raise ValueError()
                values = {key: raw[key] for key in self._keys() if key in raw}
                values['model_id'] = model.id
                if model.model == 'tecnodyne.dashboard.dataset.row':
                    values['domain_json'] = remap_dataset_domain(values.get('domain_json', '[]'), dataset_map)
                sql_sources = []
                for source in raw.get('query_sources', []):
                    sql_model = self.env['ir.model'].search([('model', '=', source['model'])], limit=1)
                    if not sql_model:
                        raise ValueError()
                    sql_fields = self.env['ir.model.fields'].search([('model_id', '=', sql_model.id), ('name', 'in', source['fields'])])
                    if len(sql_fields) != len(set(source['fields'])):
                        raise ValueError()
                    date_field = self.env['ir.model.fields'].search([('model_id', '=', sql_model.id), ('name', '=', source.get('date_field'))], limit=1) if source.get('date_field') else False
                    if source.get('date_field') and not date_field:
                        raise ValueError()
                    domain = remap_dataset_domain(source['domain_json'], dataset_map) if sql_model.model == 'tecnodyne.dashboard.dataset.row' else source['domain_json']
                    sql_sources.append((0, 0, {'alias': source['alias'], 'model_id': sql_model.id, 'field_ids': [(6, 0, sql_fields.ids)],
                                               'date_field_id': date_field.id if date_field else False, 'domain_json': domain,
                                               'date_scope': source.get('date_scope', 'range'), 'include_shared': bool(source.get('include_shared'))}))
                values['query_source_ids'] = sql_sources
                for key in ('measure_id', 'group_field_id', 'date_field_id', 'measure2_id', 'subgroup_id', 'latitude_id', 'longitude_id'):
                    field = self.env['ir.model.fields'].search([('model_id', '=', model.id), ('name', '=', raw.get(key))], limit=1) if raw.get(key) else False
                    if raw.get(key) and not field:
                        raise ValueError()
                    values[key] = field.id if field else False
                for source, key in [('list_fields', 'list_field_ids'), ('drill_fields', 'drill_field_ids'), ('extra_measures', 'extra_measure_ids')]:
                    names = raw.get(source, [])
                    if not isinstance(names, list):
                        raise ValueError()
                    found = self.env['ir.model.fields'].search([('model_id', '=', model.id), ('name', 'in', names)])
                    if len(found) != len(set(names)):
                        raise ValueError()
                    values[key] = [(6, 0, found.ids)]
                    if source == 'drill_fields':
                        by_name = {field.name: field.id for field in found}
                        values['drill_line_ids'] = [(0, 0, {'sequence': index, 'field_id': by_name[name]}) for index, name in enumerate(names)]
                currency = self.env['res.currency'].search([('name', '=', raw.get('currency'))], limit=1) if raw.get('currency') else False
                if raw.get('currency') and not currency:
                    raise ValueError()
                values['currency_id'] = currency.id if currency else False
                values['target_ids'] = [(0, 0, {'date': t['date'], 'value': t['value']}) for t in raw.get('targets', [])]
                values['task_ids'] = [(0, 0, {'name': t['name'], 'done': bool(t.get('done'))}) for t in raw.get('tasks', [])]
                if raw.get('action_xmlid'):
                    action = self.env.ref(raw['action_xmlid'])
                    if not action._name.startswith('ir.actions.'):
                        raise ValueError()
                    values['client_action_id'] = action.id
                commands.append((0, 0, values))
            if self.import_into_dashboard:
                board = self.dashboard_id
                if not board:
                    raise ValueError()
                old = board.item_ids
                board.write({'item_ids': commands})
                imported = board.item_ids - old
            else:
                board = self.env['tecnodyne.dashboard'].create({'name': data['name'], 'theme': data.get('theme', 'default'), 'layout_template': data.get('layout_template', 'balanced'), 'item_ids': commands})
                imported = board.item_ids
            by_key = {raw.get('key', str(index)): item for index, (raw, item) in enumerate(zip(data['items'], imported.sorted('id')))}
            if len(by_key) != len(imported):
                raise ValueError()
            for raw, item in zip(data['items'], imported.sorted('id')):
                if raw.get('comparison_key'):
                    if raw['comparison_key'] not in by_key:
                        raise ValueError()
                    item.comparison_item_id = by_key[raw['comparison_key']]
            for spec in data.get('filters', []):
                model = self.env['ir.model'].search([('model', '=', spec['model'])], limit=1)
                if not model:
                    raise ValueError()
                domain = remap_dataset_domain(spec['domain_json'], dataset_map) if model.model == 'tecnodyne.dashboard.dataset.row' else spec['domain_json']
                self.env['tecnodyne.dashboard.filter'].create({'name': spec['name'], 'dashboard_id': board.id, 'model_id': model.id, 'domain_json': domain})
        except (ValueError, KeyError, TypeError) as exc:
            raise ValidationError(_('Invalid or incompatible configuration. Install the required source modules first.')) from exc
        return board.action_open()

    def _reopen(self):
        return {'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': self.id,
                'views': [(False, 'form')], 'target': 'new'}
