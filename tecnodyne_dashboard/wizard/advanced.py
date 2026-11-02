import base64
import csv
import io
import json
import zipfile
from datetime import datetime

import openpyxl

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError



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
    column_types_json = fields.Text(default='{}', string='Additional column types',
        help='JSON mapping from original column names to text, integer, float, date or boolean. All original columns are retained in raw_json for snapshot SQL.')

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
            column_types = json.loads(self.column_types_json or '{}')
            if not isinstance(column_types, dict) or any(name not in headers or kind not in ('text', 'integer', 'float', 'date', 'boolean') for name, kind in column_types.items()):
                raise ValueError('Invalid additional column type mapping')
            values = []
            for source_row in rows:
                row = {key: source_row.get(column) for key, column in mapping.items() if column}
                if len(values) >= 10000:
                    raise ValueError('Maximum 10000 rows')
                if not row.get('name'):
                    continue
                original = {}
                for name, cell in source_row.items():
                    kind = column_types.get(name)
                    if cell is None or cell == '':
                        original[name] = None
                    elif kind == 'integer':
                        number = float(cell)
                        if not number.is_integer():
                            raise ValueError('Non-integer value in '+name)
                        original[name] = int(number)
                    elif kind == 'float':
                        original[name] = float(cell)
                    elif kind == 'date':
                        original[name] = str(fields.Date.to_date(cell))
                    elif kind == 'boolean':
                        text = str(cell).lower()
                        if text not in ('true', 'false', '1', '0', 'yes', 'no'):
                            raise ValueError('Invalid boolean in '+name)
                        original[name] = text in ('true', '1', 'yes')
                    else:
                        original[name] = cell.isoformat() if isinstance(cell, datetime) else str(cell) if kind == 'text' else cell
                json.dumps(original, allow_nan=False)
                value = {'name': str(row['name'])}
                value['raw_json'] = original
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
            dataset.write({'row_ids': [(5, 0, 0)] + values, 'column_types': column_types})
        else:
            dataset = self.env['tecnodyne.dashboard.dataset'].create({'name': self.name, 'company_id': self.dashboard_id.company_id.id, 'row_ids': values, 'column_types': column_types})
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

# Generation and validation are implemented in semantic.py.


class ItemTransfer(models.TransientModel):
    _name = 'tecnodyne.dashboard.move'
    _description = 'Move or duplicate dashboard item'
    item_id = fields.Many2one('tecnodyne.dashboard.item', required=True)
    dashboard_id = fields.Many2one('tecnodyne.dashboard', required=True)
    duplicate = fields.Boolean(default=True)

    def action_apply(self):
        self.ensure_one()
        return self.item_id.action_duplicate(self.dashboard_id.id) if self.duplicate else self.item_id.action_move(self.dashboard_id.id)
