"""Read-only SQL over isolated, ACL-filtered in-memory snapshots.

User SQL never runs against PostgreSQL. Each request builds a fresh SQLite
database from explicitly selected fields read through the current Odoo user.
"""
import json
import math
import re
import sqlite3
import time
from datetime import datetime, time as daytime, timedelta

import pytz
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.osv import expression
from .features import PRESETS, date_range
from .domain_security import check_domain_fields


FUNCTIONS = frozenset(('sum', 'avg', 'min', 'max', 'count', 'total', 'round', 'abs', 'coalesce', 'ifnull',
                       'nullif', 'lower', 'upper', 'trim', 'ltrim', 'rtrim', 'length', 'substr', 'substring',
                       'replace', 'date', 'datetime', 'strftime', 'julianday', 'unixepoch', 'date_trunc',
                       'row_number', 'rank', 'dense_rank', 'lag', 'lead', 'first_value', 'last_value',
                       'json_extract', 'json_array_length', 'cast', 'printf', 'like'))


class QuerySource(models.Model):
    _name = 'tecnodyne.dashboard.query.source'
    _description = 'Authorized source for dashboard SQL'
    _order = 'id'

    item_id = fields.Many2one('tecnodyne.dashboard.item', required=True, ondelete='cascade')
    alias = fields.Char(required=True, default='source')
    model_id = fields.Many2one('ir.model', required=True, ondelete='cascade')
    model_name = fields.Char(related='model_id.model')
    field_ids = fields.Many2many('ir.model.fields', string='Snapshot columns')
    date_field_id = fields.Many2one('ir.model.fields', ondelete='set null')
    domain_json = fields.Text(default='[]', required=True)
    date_scope = fields.Selection([('range', 'Selected date range'), ('as_of', 'All rows through end date')], default='range', required=True)
    include_shared = fields.Boolean(string='Include shared records without company')
    _sql_constraints = [('source_alias', 'unique(item_id,alias)', 'Source aliases must be unique inside an indicator.')]

    @api.model_create_multi
    def create(self, values_list):
        result = super().create(values_list)
        result.mapped('item_id')._refresh_watches()
        return result

    def write(self, values):
        result = super().write(values)
        self.mapped('item_id')._refresh_watches()
        return result

    def unlink(self):
        items = self.mapped('item_id')
        result = super().unlink()
        items._refresh_watches()
        return result

    @api.constrains('alias', 'field_ids', 'model_id', 'date_field_id', 'domain_json')
    def _check_source(self):
        for source in self:
            if not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_]{0,39}', source.alias or '') or source.alias.lower().startswith('sqlite_'):
                raise ValidationError(_('Use a simple SQL alias of up to 40 letters, digits or underscores.'))
            if not source.field_ids or len(source.field_ids) > 64:
                raise ValidationError(_('Choose between 1 and 64 snapshot columns.'))
            for field in source.field_ids | source.date_field_id:
                if field.model_id != source.model_id or not field.store or field.ttype not in ('char', 'text', 'boolean', 'integer', 'float', 'monetary', 'many2one', 'selection', 'date', 'datetime', 'json'):
                    raise ValidationError(_('SQL snapshots require stored scalar fields of the selected model.'))
            if source.date_field_id and source.date_field_id.ttype not in ('date', 'datetime'):
                raise ValidationError(_('Choose a date field for the snapshot range.'))
            try:
                domain = json.loads(source.domain_json)
                if not isinstance(domain, list):
                    raise ValueError()
                expression.normalize_domain(domain)
            except (ValueError, TypeError, AssertionError) as exc:
                raise ValidationError(_('Use a valid JSON domain for the source.')) from exc

    def _snapshot(self, start=False, end=False):
        self.ensure_one()
        self.check_access('read')
        self.item_id.check_access('read')
        company = self.item_id.company_id
        if company not in self.env.companies:
            raise AccessError(_('The source company is not active.'))
        target = self.env[self.model_name].with_context(allowed_company_ids=[company.id])
        target.check_access('read')
        visible = target.fields_get()
        # Elevation is limited to configured metadata, never source records.
        selected_fields = self.field_ids.sudo()
        date_field = self.date_field_id.sudo()
        names = ['id'] + [field.name for field in selected_fields if field.name != 'id']
        read_names = set(names)
        if self.date_field_id:
            read_names.add(date_field.name)
        for field in selected_fields.filtered(lambda f: f.ttype == 'monetary'):
            read_names.add(target._fields[field.name].currency_field)
        if any(name not in visible for name in read_names):
            raise AccessError(_('A selected snapshot field is restricted.'))
        def resolve(value):
            if isinstance(value, list):
                return [resolve(v) for v in value]
            if isinstance(value, str) and value in ('$uid', '%UID'):
                return self.env.uid
            if isinstance(value, str) and value in ('$company', '%MYCOMPANY', '%MY COMPANY'):
                return company.id
            return value
        domain = resolve(json.loads(self.domain_json))
        if 'company_id' in target._fields:
            domain = expression.AND([domain, [('company_id', 'in', [company.id, False])] if self.include_shared else [('company_id', '=', company.id)]])
        if self.date_scope == 'as_of':
            start, end = False, end or fields.Date.context_today(self)
        if start and end and fields.Date.to_date(start) > fields.Date.to_date(end):
            raise ValidationError(_('Start date must precede end date.'))
        if self.date_field_id:
            def boundary(day):
                if date_field.ttype == 'date':
                    return str(day)
                local = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC').localize(datetime.combine(day, daytime.min))
                return fields.Datetime.to_string(local.astimezone(pytz.UTC).replace(tzinfo=None))
            if start:
                domain = expression.AND([domain, [(date_field.name, '>=', boundary(fields.Date.to_date(start)))]])
            if end:
                domain = expression.AND([domain, [(date_field.name, '<', boundary(fields.Date.to_date(end)+timedelta(days=1)))]])
        for filter in self.item_id.dashboard_id.filter_ids.filtered(lambda f: f.id in self.env.context.get('td_filters', []) and f.model_id == self.model_id):
            domain = expression.AND([domain, resolve(json.loads(filter.domain_json))])
        check_domain_fields(target, domain)
        records = target.search_read(domain, list(read_names), limit=10001, order='id')
        if len(records) > 10000:
            raise UserError(_('A SQL source exceeds 10,000 authorized rows. Narrow its domain or dates.'))
        columns = list(names)
        for field in selected_fields.filtered(lambda f: f.ttype == 'many2one'):
            columns.append(field.name+'__name')
        rows = []
        for record in records:
            values = {}
            for name in names:
                value = record[name]
                field = target._fields[name]
                if field.type == 'many2one':
                    values[name] = value[0] if value else None
                    values[name+'__name'] = value[1] if value else None
                elif field.type == 'monetary':
                    currency_value = record.get(field.currency_field)
                    currency = self.env['res.currency'].browse(currency_value[0]) if currency_value else company.currency_id
                    day = fields.Date.to_date(record.get(date_field.name)) if date_field and record.get(date_field.name) else fields.Date.context_today(self)
                    values[name] = currency._convert(value or 0, company.currency_id, company, day)
                elif isinstance(value, (dict, list)):
                    values[name] = json.dumps(value, default=str)
                elif value is False and field.type not in ('boolean', 'integer', 'float'):
                    values[name] = None
                elif isinstance(value, (str, int, float)) or value is None:
                    values[name] = value
                else:
                    values[name] = str(value)
            rows.append([values.get(name) for name in columns])
        return columns, rows, domain


class SQLItem(models.Model):
    _inherit = 'tecnodyne.dashboard.item'

    query_mode = fields.Selection([('orm', 'Odoo model'), ('sql', 'SQL over authorized snapshots')], default='orm', required=True)
    query_sql = fields.Text(default='SELECT name AS label, SUM(value) AS value FROM source GROUP BY name')
    query_source_ids = fields.One2many('tecnodyne.dashboard.query.source', 'item_id', copy=True)

    @api.constrains('query_mode', 'query_sql', 'kind')
    def _check_sql(self):
        for item in self.filtered(lambda i: i.query_mode == 'sql'):
            if item.kind == 'todo':
                raise ValidationError(_('SQL results cannot be used as an editable checklist.'))
            if not item.query_sql or len(item.query_sql) > 20000 or not re.match(r'^\s*(select|with)\b', item.query_sql, re.I):
                raise ValidationError(_('Enter a read-only SELECT or WITH query, up to 20,000 characters.'))

    def _run_snapshot_query(self, start=False, end=False):
        self.ensure_one()
        self.check_access('read')
        self.dashboard_id.check_access('read')
        sources = self.query_source_ids
        if not 1 <= len(sources) <= 5:
            raise ValidationError(_('Configure between 1 and 5 SQL sources.'))
        preset = self.preset if self.preset != 'custom' else self.env.context.get('td_preset', 'custom')
        if preset not in dict(PRESETS):
            raise ValidationError(_('Unknown date range.'))
        if preset != 'custom':
            start, end = date_range(preset, fields.Date.context_today(self))
        db = sqlite3.connect(':memory:')
        try:
            db.enable_load_extension(False)
            db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 5*1024*1024)
            db.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 20000)
            db.setlimit(sqlite3.SQLITE_LIMIT_COLUMN, 200)
            aliases, size = set(), 0
            for source in sources:
                columns, records, domain = source._snapshot(start, end)
                size += len(records)
                if size > 20000:
                    raise UserError(_('SQL sources exceed 20,000 rows in total. Narrow the query inputs.'))
                aliases.add(source.alias.lower())
                quote = lambda value: '"'+value.replace('"', '""')+'"'
                db.execute('CREATE TABLE '+quote(source.alias)+' ('+', '.join(quote(name) for name in columns)+')')
                db.executemany('INSERT INTO '+quote(source.alias)+' VALUES ('+', '.join('?' for name in columns)+')', records)
            def truncate(unit, value):
                if value is None:
                    return None
                text = str(value)
                return text[:4]+'-01-01' if unit == 'year' else text[:7]+'-01' if unit == 'month' else text[:10] if unit == 'day' else None
            db.create_function('date_trunc', 2, truncate, deterministic=True)
            def authorize(action, first, second, database, origin):
                if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_RECURSIVE):
                    return sqlite3.SQLITE_OK
                if action == sqlite3.SQLITE_READ and first.lower() in aliases:
                    return sqlite3.SQLITE_OK
                if action == sqlite3.SQLITE_FUNCTION and (second or first or '').lower() in FUNCTIONS:
                    return sqlite3.SQLITE_OK
                return sqlite3.SQLITE_DENY
            db.set_authorizer(authorize)
            deadline, ticks = time.monotonic()+3, [0]
            def progress():
                ticks[0] += 1
                return int(ticks[0] > 10000 or time.monotonic() > deadline)
            db.set_progress_handler(progress, 1000)
            sql = self.query_sql
            for token, parameter in [('%MY COMPANY', ':company'), ('%MYCOMPANY', ':company'), ('%UID', ':uid')]:
                sql = sql.replace("'"+token+"'", parameter).replace(token, parameter)
            cursor = db.execute(sql, {'uid': self.env.uid, 'company': self.company_id.id, 'date_from': str(start) if start else None, 'date_to': str(end) if end else None})
            names = [column[0] for column in cursor.description or []]
            if len(names) != len(set(names)) or 'label' not in names or 'value' not in names:
                raise ValidationError(_('SQL results require unique columns named label and value. Optional: series, value2, record_id, source_alias, lat, lon.'))
            result, byte_count = [], 0
            for row in cursor:
                byte_count += sum(len(value.encode('utf-8')) if isinstance(value, str) else 8 for value in row)
                if len(result) >= 10000 or byte_count > 10*1024*1024:
                    raise UserError(_('SQL result exceeds 10,000 rows or 10 MB. Narrow the query; no partial result was returned.'))
                result.append(dict(zip(names, row)))
            for row in result:
                for key in ('value', 'value2', 'lat', 'lon'):
                    if key in row and row[key] is not None and (not isinstance(row[key], (int, float)) or not math.isfinite(row[key])):
                        raise ValidationError(_('SQL measures and coordinates must be finite numbers.'))
            return names, result
        except sqlite3.Error as exc:
            raise ValidationError(_('The read-only snapshot query failed: %s', str(exc))) from exc
        finally:
            db.close()

    def _payload(self, date_from=False, date_to=False, export=False):
        if self.query_mode != 'sql':
            return super()._payload(date_from, date_to, export=export)
        names, records = self._run_snapshot_query(date_from, date_to)
        page = 0 if export else max(0, min(1000, int(self.env.context.get('td_page', 0))))
        cap = 10000 if export else self.limit
        rows = []
        for record in records[page*cap:(page+1)*cap]:
            rows.append({'label': str(record['label'] if record['label'] is not None else ''), 'value': record['value'] or 0,
                         'series': str(record.get('series') or ''), 'value2': record.get('value2') or 0,
                         'lat': record.get('lat'), 'lon': record.get('lon'), 'target': self.target,
                         'record_id': record.get('record_id'), 'source_alias': record.get('source_alias'),
                         'cells': [record.get(name) for name in names] if self.kind in ('list', 'table') else None})
        return {'id': self.id, 'name': self.name, 'kind': self.kind, 'source_kind': self.kind,
                'value': records[0]['value'] or 0 if records and self.kind == 'kpi' else 0,
                'rows': rows, 'columns': names if self.kind in ('list', 'table') else [], 'limit': self.limit,
                'page': page, 'total': len(records), 'target': self.target, 'unit': self.unit or '',
                'icon': self.icon, 'color': self.color, 'show_values': self.show_values, 'show_legend': self.show_legend,
                'has_second': 'value2' in names, 'measure_labels': {}, 'stacked': self.stacked,
                'number_format': self.number_format, 'tile_style': self.tile_style, 'target_style': self.target_style,
                'level': 0, 'depth': 0, 'sequence': self.sequence, 'targets': {}, 'secondary_as_line': self.secondary_as_line,
                'cumulative_as_line': False}

    def action_drill(self, row_index=False, date_from=False, date_to=False, preset='custom', filter_ids=None, path=None, page=0):
        if self.query_mode != 'sql':
            return super().action_drill(row_index, date_from, date_to, preset, filter_ids, path, page)
        item = self.with_context(td_preset=preset, td_filters=filter_ids or [], td_page=page)
        payload = item._payload(date_from, date_to)
        if type(row_index) is not int or not 0 <= row_index < len(payload['rows']):
            raise UserError(_('Select a SQL result row with a source_alias and record_id to open its source record.'))
        row = payload['rows'][row_index]
        source = item.query_source_ids.filtered(lambda s: s.alias == row.get('source_alias'))
        if len(source) != 1 or type(row.get('record_id')) is not int:
            raise UserError(_('This SQL aggregate does not identify a source record. Include source_alias and record_id in the SELECT to enable record navigation.'))
        effective_preset = self.preset if self.preset != 'custom' else preset
        if effective_preset != 'custom':
            date_from, date_to = date_range(effective_preset, fields.Date.context_today(self))
        columns, records, domain = source._snapshot(date_from, date_to)
        ids = {record[columns.index('id')] for record in records}
        if row['record_id'] not in ids:
            raise AccessError(_('The SQL result does not refer to an authorized source record.'))
        return {'type': 'ir.actions.act_window', 'name': self.name, 'res_model': source.model_name,
                'res_id': row['record_id'], 'views': [(False, 'form')],
                'context': {'allowed_company_ids': [self.company_id.id]}}
