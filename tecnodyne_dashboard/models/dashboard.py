import json
from datetime import datetime, time, timedelta
import pytz

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv import expression


class Dashboard(models.Model):
    _name = 'tecnodyne.dashboard'
    _description = 'Tecnodyne Dashboard'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda s: s.env.company)
    group_ids = fields.Many2many('res.groups', string='Viewer groups')
    item_ids = fields.One2many('tecnodyne.dashboard.item', 'dashboard_id', copy=True)

    def action_open(self):
        self.ensure_one()
        self.check_access('read')
        return {'type': 'ir.actions.client', 'tag': 'tecnodyne_dashboard',
                'name': self.name, 'params': {'dashboard_id': self.id}}

    def get_dashboard(self, date_from=False, date_to=False):
        self.ensure_one()
        self.check_access('read')
        result = []
        for item in self.item_ids:
            # Deliberately fail closed: no sudo, no cached cross-user data.
            result.append(item._payload(date_from, date_to))
        return {'name': self.name, 'company': self.company_id.name, 'items': result}


class DashboardItem(models.Model):
    _name = 'tecnodyne.dashboard.item'
    _description = 'Tecnodyne Dashboard Item'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    dashboard_id = fields.Many2one('tecnodyne.dashboard', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='dashboard_id.company_id', store=True)
    model_id = fields.Many2one('ir.model', required=True, ondelete='cascade')
    model_name = fields.Char(related='model_id.model')
    kind = fields.Selection([('kpi', 'KPI'), ('bar', 'Bars'), ('line', 'Line'),
                             ('pie', 'Pie'), ('table', 'Grouped table')], default='kpi', required=True)
    aggregation = fields.Selection([('count', 'Count'), ('sum', 'Sum'), ('avg', 'Average'),
                                    ('min', 'Minimum'), ('max', 'Maximum')], default='count', required=True)
    measure_id = fields.Many2one('ir.model.fields', ondelete='set null', string='Numeric measure')
    group_field_id = fields.Many2one('ir.model.fields', ondelete='set null', string='Group by')
    date_field_id = fields.Many2one('ir.model.fields', ondelete='set null', string='Date filter field')
    interval = fields.Selection([('day', 'Day'), ('week', 'Week'), ('month', 'Month'),
                                 ('quarter', 'Quarter'), ('year', 'Year')], default='month', required=True)
    domain_json = fields.Text(default='[]', required=True, help='JSON domain. Values $uid and $company are resolved at read time.')
    limit = fields.Integer(default=20, required=True)
    target = fields.Float()
    unit = fields.Char(help='Display label only. No automatic currency conversion.')

    @api.constrains('model_id', 'measure_id', 'group_field_id', 'date_field_id', 'aggregation', 'kind', 'domain_json', 'limit')
    def _validate_configuration(self):
        for item in self:
            if not 1 <= item.limit <= 200:
                raise ValidationError(_('Group limit must be between 1 and 200.'))
            for field in item.measure_id | item.group_field_id | item.date_field_id:
                if field.model_id != item.model_id or not field.store:
                    raise ValidationError(_('Choose stored fields from the selected model.'))
            if item.aggregation != 'count' and (not item.measure_id or item.measure_id.ttype not in ('integer', 'float', 'monetary')):
                raise ValidationError(_('Select a stored numeric measure.'))
            if item.kind != 'kpi' and not item.group_field_id:
                raise ValidationError(_('A grouping field is required.'))
            if item.group_field_id and item.group_field_id.ttype not in ('many2one', 'char', 'selection', 'boolean', 'date', 'datetime', 'integer'):
                raise ValidationError(_('Unsupported grouping field.'))
            if item.date_field_id and item.date_field_id.ttype not in ('date', 'datetime'):
                raise ValidationError(_('Select a date or datetime field.'))
            item._domain()

    def _domain(self):
        self.ensure_one()
        try:
            domain = json.loads(self.domain_json)
            if not isinstance(domain, list):
                raise ValueError()
            def replace(value):
                if isinstance(value, list):
                    return [replace(v) for v in value]
                if value == '$uid':
                    return self.env.uid
                if value == '$company':
                    return self.company_id.id
                return value
            domain = replace(domain)
            expression.normalize_domain(domain)
            return domain
        except (ValueError, TypeError, AssertionError) as exc:
            raise ValidationError(_('The domain must be a valid JSON Odoo domain.')) from exc

    def _query(self, date_from=False, date_to=False):
        self.ensure_one()
        self.check_access('read')
        self.dashboard_id.check_access('read')
        # Record rules of the target model remain in force. Restrict context to ONE
        # authorized company to prevent mixed-company monetary totals.
        if self.company_id not in self.env.companies:
            raise ValidationError(_('Select the dashboard company in the company selector.'))
        target = self.env[self.model_name].with_context(allowed_company_ids=[self.company_id.id])
        target.check_access('read')
        visible = target.fields_get()
        for f in self.measure_id | self.group_field_id | self.date_field_id:
            if f.name not in visible:
                raise ValidationError(_('You cannot read a configured dashboard field.'))
        domain = self._domain()
        if 'company_id' in target._fields:
            domain = expression.AND([domain, [('company_id', '=', self.company_id.id)]])
        if self.date_field_id:
            field = self.date_field_id.name
            start = fields.Date.to_date(date_from) if date_from else False
            end = fields.Date.to_date(date_to) if date_to else False
            if start and end and start > end:
                raise ValidationError(_('Start date must precede end date.'))
            def boundary(day):
                if self.date_field_id.ttype == 'date':
                    return str(day)
                zone = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
                local = zone.localize(datetime.combine(day, time.min))
                return fields.Datetime.to_string(local.astimezone(pytz.UTC).replace(tzinfo=None))
            if start:
                domain = expression.AND([domain, [(field, '>=', boundary(start))]])
            if end:
                domain = expression.AND([domain, [(field, '<', boundary(end + timedelta(days=1)))]])
        return target, domain

    def _payload(self, date_from=False, date_to=False):
        target, domain = self._query(date_from, date_to)
        measure = self.measure_id.name if self.aggregation != 'count' else False
        aggregate = (measure + ':' + self.aggregation) if measure else None
        group = self.group_field_id.name
        if self.group_field_id.ttype in ('date', 'datetime'):
            group += ':' + self.interval
        rows = []
        if self.kind == 'kpi':
            value = target.read_group(domain, [aggregate], [], lazy=False)[0].get(measure, 0) if aggregate else target.search_count(domain)
        else:
            groups = target.read_group(domain, [group] + ([aggregate] if aggregate else []), [group],
                                       limit=self.limit, lazy=False)
            for row in groups:
                label = row.get(group, False)
                if isinstance(label, tuple):
                    label = label[1]
                rows.append({'label': str(label) if label is not False else _('Undefined'),
                             'value': (row.get(measure, 0) if measure else row.get('__count', 0)) or 0,
                             'domain': row['__domain']})
            value = False
        return {'id': self.id, 'name': self.name, 'kind': self.kind, 'value': value or 0,
                'rows': rows, 'target': self.target, 'unit': self.unit or '', 'limit': self.limit}

    def action_drill(self, row_index=False, date_from=False, date_to=False):
        self.ensure_one()
        target, domain = self._query(date_from, date_to)
        if row_index is not False:
            rows = self._payload(date_from, date_to)['rows']
            if type(row_index) is not int or not 0 <= row_index < len(rows):
                raise ValidationError(_('Invalid group.'))
            domain = rows[row_index]['domain']
        return {'type': 'ir.actions.act_window', 'name': self.name, 'res_model': target._name,
                'views': [(False, 'list'), (False, 'form')], 'domain': domain,
                'context': {'allowed_company_ids': [self.company_id.id]}}
