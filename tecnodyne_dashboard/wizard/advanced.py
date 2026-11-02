import base64
import csv
import io
import json
import zipfile
from datetime import datetime

import openpyxl

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from odoo.osv import expression


class ImportData(models.TransientModel):
    _name = 'tecnodyne.dashboard.import'
    _description = 'Import CSV or Excel dashboard source'

    name = fields.Char(required=True, default='Imported data')
    file = fields.Binary(required=True)
    filename = fields.Char(required=True)
    dataset_id = fields.Many2one('tecnodyne.dashboard.dataset', string='Replace existing dataset')
    dashboard_id = fields.Many2one('tecnodyne.dashboard', required=True)
    label_column = fields.Char(default='name', required=True)
    category_column = fields.Char(default='category')
    value_column = fields.Char(default='value')
    value2_column = fields.Char(default='value2')
    date_column = fields.Char(default='date')
    latitude_column = fields.Char(default='latitude')
    longitude_column = fields.Char(default='longitude')
    amount_column = fields.Char(default='amount')
    currency_column = fields.Char(default='currency')

    def action_import(self):
        self.ensure_one()
        self.dashboard_id.check_access('write')
        content = base64.b64decode(self.file)
        if len(content) > 5*1024*1024:
            raise ValidationError(_('Maximum file size is 5 MB.'))
        try:
            if self.filename.lower().endswith('.xlsx'):
                with zipfile.ZipFile(io.BytesIO(content)) as archive:
                    if sum(f.file_size for f in archive.infolist()) > 50*1024*1024:
                        raise ValueError('Workbook too large')
                book = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
                iterator = book.active.iter_rows(values_only=True)
                headers = list(next(iterator))
                rows = (dict(zip(headers, row)) for row in iterator)
            elif self.filename.lower().endswith('.csv'):
                rows = csv.DictReader(io.StringIO(content.decode('utf-8-sig')))
                headers = rows.fieldnames or []
            else:
                raise ValueError('CSV or XLSX required')
            mapping = {'name': self.label_column, 'category': self.category_column, 'value': self.value_column,
                       'value2': self.value2_column, 'date': self.date_column, 'latitude': self.latitude_column,
                       'longitude': self.longitude_column, 'amount': self.amount_column, 'currency': self.currency_column}
            if self.label_column not in headers:
                raise ValueError('The label column was not found in the file')
            values = []
            for source_row in rows:
                row = {key: source_row.get(column) for key, column in mapping.items() if column}
                if len(values) >= 10000:
                    raise ValueError('Maximum 10000 rows')
                if not row.get('name'):
                    continue
                value = {'name': str(row['name'])}
                if row.get('category') is not None:
                    value['category'] = str(row['category'])
                for key in ('value', 'value2', 'latitude', 'longitude', 'amount'):
                    value[key] = float(row.get(key) or 0)
                if row.get('currency'):
                    currency = self.env['res.currency'].search([('name', '=', str(row['currency']).upper())], limit=1)
                    if not currency:
                        raise ValueError('Unknown currency code')
                    value['currency_id'] = currency.id
                if row.get('date'):
                    day = row['date'].date() if isinstance(row['date'], datetime) else fields.Date.to_date(row['date'])
                    value['date'] = day
                if not -90 <= value['latitude'] <= 90 or not -180 <= value['longitude'] <= 180:
                    raise ValueError('Invalid coordinates')
                values.append((0, 0, value))
            if self.filename.lower().endswith('.xlsx'):
                book.close()
        except (ValueError, TypeError, KeyError, StopIteration, zipfile.BadZipFile) as exc:
            raise ValidationError(_('Invalid import: %s', str(exc))) from exc
        dataset = self.dataset_id
        if dataset:
            dataset.check_access('write')
            if dataset.company_id != self.dashboard_id.company_id:
                raise ValidationError(_('Dataset and dashboard must belong to the same company.'))
            dataset.write({'row_ids': [(5, 0, 0)] + values})
        else:
            dataset = self.env['tecnodyne.dashboard.dataset'].create({'name': self.name, 'company_id': self.dashboard_id.company_id.id, 'row_ids': values})
            model = 'tecnodyne.dashboard.dataset.row'
            self.env['tecnodyne.dashboard.item'].create({
                'name': self.name, 'dashboard_id': self.dashboard_id.id, 'kind': 'bar',
                'model_id': self.env['ir.model']._get_id(model), 'aggregation': 'sum',
                'measure_id': self.env['ir.model.fields']._get(model, 'value').id,
                'group_field_id': self.env['ir.model.fields']._get(model, 'category').id,
                'date_field_id': self.env['ir.model.fields']._get(model, 'date').id,
                'domain_json': json.dumps([['dataset_id', '=', dataset.id]]),
            })
        return self.dashboard_id.action_open()


class GenerateAI(models.TransientModel):
    _name = 'tecnodyne.dashboard.generate'
    _description = 'Generate dashboard or items with local AI'

    name = fields.Char(default='AI dashboard', required=True)
    model_id = fields.Many2one('ir.model', required=True, ondelete='cascade')
    dashboard_id = fields.Many2one('tecnodyne.dashboard', string='Existing dashboard (optional)')
    keywords = fields.Text(string='What would you like to analyze?', required=True)
    item_count = fields.Integer(string='Maximum indicators', default=3, required=True)
    proposal = fields.Text(readonly=True)

    @api.constrains('item_count')
    def _check_item_count(self):
        if any(not 1 <= wizard.item_count <= 12 for wizard in self):
            raise ValidationError(_('Choose between 1 and 12 indicators.'))

    def action_generate(self):
        self.ensure_one()
        target = self.env[self.model_id.model]
        target.check_access('read')
        # Schema only; record values are not needed to propose queries.
        schema = {n: {'type': f['type'], 'label': f['string']} for n, f in target.fields_get().items()
                  if target._fields[n].store and f['type'] in ('char', 'selection', 'many2one', 'date', 'datetime', 'integer', 'float', 'monetary')}
        prompt = (f'Create an Odoo dashboard JSON proposal, max {self.item_count} items. '
                  'Return only JSON in this shape: {"items":[{"name":"Conteo de registros","kind":"kpi","aggregation":"count","measure":null,"group":null,"date":null,"domain":[]}]}.'
                  ' Allowed kind values: kpi, bar, line, pie, table. Allowed aggregation values: count, sum, avg.'
                  ' The measure, group and date values must be exact supplied field names or JSON null (not the string "null"). Count requires measure:null.'
                  ' Use only supplied stored schema fields. Sum/avg require a numeric measure. Non-KPI items require a grouping field.'
                  ' Use neutral titles describing the exact query; do not call invoices cash liquidity or claim paid/unpaid totals without a matching domain.'
                  ' If the schema cannot answer the request, return {"items":[]}. Never use code or SQL. User request: '
                  + self.keywords + '\nSchema: ' + json.dumps(schema))
        raw = self.env['tecnodyne.dashboard.ai']._generate(prompt, json_mode=True)
        commands = self._validated_items(raw)
        self.proposal = raw
        return {'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': self.id, 'views': [(False, 'form')], 'target': 'new'}

    def _validated_items(self, raw):
        try:
            data = json.loads(raw)
            if not isinstance(data, dict) or not isinstance(data.get('items'), list) or not 1 <= len(data['items']) <= self.item_count:
                raise ValueError()
            commands = []
            visible = self.env[self.model_id.model].fields_get()
            for spec in data['items']:
                if spec['kind'] not in ('kpi', 'bar', 'line', 'pie', 'table') or spec['aggregation'] not in ('count', 'sum', 'avg'):
                    raise ValueError()
                values = {'name': str(spec['name'])[:150], 'model_id': self.model_id.id, 'kind': spec['kind'], 'aggregation': spec['aggregation'],
                          'domain_json': json.dumps(spec.get('domain', []))}
                domain = spec.get('domain', [])
                if not isinstance(domain, list):
                    raise ValueError()
                expression.normalize_domain(domain)
                for leaf in domain:
                    if isinstance(leaf, (list, tuple)) and (len(leaf) != 3 or leaf[0] not in visible):
                        raise ValueError()
                for source, key in [('measure', 'measure_id'), ('group', 'group_field_id'), ('date', 'date_field_id')]:
                    name = spec.get(source)
                    if name and name not in visible:
                        raise ValueError()
                    if name and not self.env[self.model_id.model]._fields[name].store:
                        raise ValueError()
                    if source == 'measure' and spec['aggregation'] != 'count' and (not name or visible[name]['type'] not in ('integer', 'float', 'monetary')):
                        raise ValueError()
                    if source == 'group' and (spec['kind'] != 'kpi' and not name or name and visible[name]['type'] not in ('many2one', 'char', 'selection', 'boolean', 'date', 'datetime', 'integer')):
                        raise ValueError()
                    if source == 'date' and name and visible[name]['type'] not in ('date', 'datetime'):
                        raise ValueError()
                    values[key] = self.env['ir.model.fields']._get(self.model_id.model, name).id if name else False
                commands.append((0, 0, values))
            return commands
        except (ValueError, TypeError, KeyError, AssertionError) as exc:
            raise ValidationError(_('The AI proposal is incompatible. Refine the request and generate again.')) from exc

    def action_apply(self):
        self.ensure_one()
        if not self.proposal:
            raise UserError(_('Generate and review a proposal first.'))
        commands = self._validated_items(self.proposal)
        board = self.dashboard_id
        if board:
            board.write({'item_ids': commands})
        else:
            board = self.env['tecnodyne.dashboard'].create({'name': self.name, 'item_ids': commands})
        return board.action_open()


class ItemTransfer(models.TransientModel):
    _name = 'tecnodyne.dashboard.move'
    _description = 'Move or duplicate dashboard item'
    item_id = fields.Many2one('tecnodyne.dashboard.item', required=True)
    dashboard_id = fields.Many2one('tecnodyne.dashboard', required=True)
    duplicate = fields.Boolean(default=True)

    def action_apply(self):
        self.ensure_one()
        return self.item_id.action_duplicate(self.dashboard_id.id) if self.duplicate else self.item_id.action_move(self.dashboard_id.id)
