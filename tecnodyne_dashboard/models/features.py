import base64
import csv
import io
import json
import math
from datetime import timedelta

from dateutil.relativedelta import relativedelta
import requests
import xlsxwriter

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError, UserError
from odoo.osv import expression


KINDS = [('horizontal', 'Horizontal bars'), ('area', 'Area'), ('doughnut', 'Doughnut'),
         ('polarArea', 'Polar area'), ('radar', 'Radar'), ('scatter', 'Scatter'),
         ('flower', 'Flower'), ('funnel', 'Funnel'), ('radial', 'Radial'),
         ('bullet', 'Bullet'), ('map', 'Map'), ('todo', 'To-do'), ('list', 'Records')]
PRESETS = [('custom', 'Custom / dashboard'), ('today', 'Today'), ('yesterday', 'Yesterday'),
           ('tomorrow', 'Tomorrow'), ('this_week', 'This week'), ('last_week', 'Last week'),
           ('next_week', 'Next week'), ('this_month', 'This month'), ('last_month', 'Last month'),
           ('next_month', 'Next month'), ('this_quarter', 'This quarter'), ('last_quarter', 'Last quarter'),
           ('next_quarter', 'Next quarter'), ('this_year', 'This year'), ('last_year', 'Last year'),
           ('next_year', 'Next year'), ('week_to_date', 'Week to date'), ('month_to_date', 'Month to date'),
           ('quarter_to_date', 'Quarter to date'), ('year_to_date', 'Year to date'),
           ('last_7', 'Last 7 days'), ('last_30', 'Last 30 days'), ('last_90', 'Last 90 days'),
           ('last_365', 'Last 365 days'), ('next_7', 'Next 7 days'), ('next_30', 'Next 30 days'),
           ('next_90', 'Next 90 days'), ('all', 'All time')]


def date_range(key, today):
    if key in ('custom', 'all', False):
        return False, False
    if key == 'today':
        return today, today
    if key in ('yesterday', 'tomorrow'):
        day = today + timedelta(days=-1 if key == 'yesterday' else 1)
        return day, day
    if key.startswith(('last_', 'next_')) and key.split('_')[1].isdigit():
        days = int(key.split('_')[1])
        return (today - timedelta(days=days-1), today) if key.startswith('last') else (today, today + timedelta(days=days-1))
    period = key.split('_')[1] if key.startswith(('this_', 'last_', 'next_')) else key.split('_')[0]
    if period == 'week':
        start, delta = today - timedelta(days=today.weekday()), relativedelta(weeks=1)
    elif period == 'month':
        start, delta = today.replace(day=1), relativedelta(months=1)
    elif period == 'quarter':
        start, delta = today.replace(month=((today.month-1)//3)*3+1, day=1), relativedelta(months=3)
    elif period == 'year':
        start, delta = today.replace(month=1, day=1), relativedelta(years=1)
    else:
        raise ValidationError(_('Unknown date range.'))
    if key.startswith('last_'):
        start -= delta
    elif key.startswith('next_'):
        start += delta
    return start, today if key.endswith('_to_date') else start + delta - timedelta(days=1)


class Dashboard(models.Model):
    _inherit = 'tecnodyne.dashboard'

    theme = fields.Selection([('default', 'Ocean'), ('cool', 'Cool'), ('warm', 'Warm'), ('neon', 'Neon')], default='default', required=True)
    layout_template = fields.Selection([('balanced', 'Balanced grid'), ('featured', 'Featured first item'), ('full', 'Full-width rows')], default='balanced', required=True)
    action_id = fields.Many2one('ir.actions.client', copy=False, readonly=True)
    filter_ids = fields.One2many('tecnodyne.dashboard.filter', 'dashboard_id', copy=True)
    template = fields.Selection([('sale', 'Sales'), ('crm', 'CRM'), ('account', 'Accounting'), ('stock', 'Inventory'), ('pos', 'POS')])

    def get_dashboard(self, date_from=False, date_to=False, preset='custom', filter_ids=None):
        self.ensure_one()
        self.check_access('read')
        if preset not in dict(PRESETS):
            raise ValidationError(_('Unknown date range.'))
        filters = self.filter_ids.filtered(lambda f: f.id in (filter_ids or []))
        if len(filters) != len(set(filter_ids or [])):
            raise AccessError(_('Invalid dashboard filter.'))
        context = dict(self.env.context, td_preset=preset, td_filters=filters.ids)
        # Search, rather than reading the one2many, applies per-item audience rules.
        items = self.env['tecnodyne.dashboard.item'].search([('dashboard_id', '=', self.id)])
        preference = self.env['tecnodyne.dashboard.preference'].search([('dashboard_id', '=', self.id), ('user_id', '=', self.env.uid)], limit=1)
        default_layout = {str(item.id): {'order': index, 'width': 3 if self.layout_template == 'full' else 2 if self.layout_template == 'featured' and index == 0 else 1, 'height': 420} for index, item in enumerate(items)}
        return {'id': self.id, 'name': self.name, 'company': self.company_id.name, 'theme': self.theme,
                'items': [item.with_context(context)._payload(date_from, date_to) for item in items],
                'presets': self.env['tecnodyne.dashboard.item']._fields['preset']._description_selection(self.env), 'filters': [{'id': f.id, 'name': f.name} for f in self.filter_ids],
                'layout': preference.layout or default_layout, 'layouts': list(preference.saved_layouts or {}), 'favorite': bool(preference.favorite),
                'designer': self.env.user.has_group('tecnodyne_dashboard.group_dashboard_manager')}

    def save_preferences(self, layout=None, favorite=None):
        self.ensure_one()
        self.check_access('read')
        prefs = self.env['tecnodyne.dashboard.preference'].search([('dashboard_id', '=', self.id), ('user_id', '=', self.env.uid)], limit=1)
        values = {}
        if layout is not None:
            if not isinstance(layout, dict) or len(json.dumps(layout)) > 50000:
                raise ValidationError(_('Invalid layout.'))
            allowed = set(self.env['tecnodyne.dashboard.item'].search([('dashboard_id', '=', self.id)]).ids)
            clean = {}
            for key, value in layout.items():
                if not str(key).isdigit() or int(key) not in allowed or not isinstance(value, dict):
                    raise ValidationError(_('Invalid layout item.'))
                clean[str(key)] = {'order': max(0, min(1000, int(value.get('order', 0)))),
                                   'width': max(1, min(3, int(value.get('width', 1)))),
                                   'height': max(250, min(1000, int(value.get('height', 350))))}
            values['layout'] = clean
        if favorite is not None:
            values['favorite'] = bool(favorite)
        if prefs:
            prefs.write(values)
        else:
            self.env['tecnodyne.dashboard.preference'].create(dict(values, dashboard_id=self.id, user_id=self.env.uid))
        return True

    def save_named_layout(self, name, layout):
        self.ensure_one()
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 60:
            raise ValidationError(_('Choose a layout name up to 60 characters.'))
        self.save_preferences(layout=layout)
        pref = self.env['tecnodyne.dashboard.preference'].search([('dashboard_id', '=', self.id), ('user_id', '=', self.env.uid)], limit=1)
        saved = dict(pref.saved_layouts or {})
        if len(saved) >= 20 and name not in saved:
            raise ValidationError(_('Maximum 20 personal layouts.'))
        saved[name] = pref.layout
        pref.saved_layouts = saved
        return list(saved)

    def select_named_layout(self, name):
        self.ensure_one()
        self.check_access('read')
        pref = self.env['tecnodyne.dashboard.preference'].search([('dashboard_id', '=', self.id), ('user_id', '=', self.env.uid)], limit=1)
        layout = (pref.saved_layouts or {}).get(name)
        if layout is None:
            raise ValidationError(_('Unknown personal layout.'))
        self.save_preferences(layout=layout)
        return layout

    def action_publish_menu(self):
        self.ensure_one()
        self.check_access('write')
        if not self.env.user.has_group('base.group_system'):
            raise AccessError(_('Only a settings administrator can publish menus.'))
        values = {'name': self.name, 'tag': 'tecnodyne_dashboard', 'params': {'dashboard_id': self.id}}
        if self.action_id:
            self.action_id.write(values)
        else:
            self.action_id = self.env['ir.actions.client'].create(values)
            self.env['ir.ui.menu'].create({'name': self.name, 'parent_id': self.env.ref('tecnodyne_dashboard.dashboard_root').id,
                                           'action': 'ir.actions.client,%s' % self.action_id.id,
                                           'groups_id': [(6, 0, self.group_ids.ids or [self.env.ref('tecnodyne_dashboard.group_dashboard_user').id])]})
        return True

    def action_apply_template(self):
        self.ensure_one()
        self.check_access('write')
        spec = {'sale': ('sale.order', 'amount_total', 'partner_id', 'date_order'),
                'crm': ('crm.lead', 'expected_revenue', 'stage_id', 'create_date'),
                'account': ('account.move.line', 'balance', 'account_id', 'date'),
                'stock': ('stock.quant', 'quantity', 'product_id', 'create_date'),
                'pos': ('pos.order', 'amount_total', 'session_id', 'date_order')}.get(self.template)
        if not spec or spec[0] not in self.env:
            raise UserError(_('Install the source application and choose a template first.'))
        model, measure, group, date = spec
        def field(name):
            return self.env['ir.model.fields']._get(model, name).id
        common = {'dashboard_id': self.id, 'model_id': self.env['ir.model']._get_id(model), 'date_field_id': field(date)}
        self.env['tecnodyne.dashboard.item'].create([
            dict(common, name=_('Record count'), kind='kpi'),
            dict(common, name=_('Total'), kind='kpi', aggregation='sum', measure_id=field(measure)),
            dict(common, name=_('By category'), kind='bar', aggregation='sum', measure_id=field(measure), group_field_id=field(group)),
            dict(common, name=_('Trend'), kind='line', aggregation='sum', measure_id=field(measure), group_field_id=field(date)),
        ])
        return self.action_open()


class Item(models.Model):
    _inherit = ['tecnodyne.dashboard.item', 'mail.thread']
    _name = 'tecnodyne.dashboard.item'
    _mail_post_access = 'read'

    kind = fields.Selection(selection_add=KINDS, ondelete={key: 'set default' for key, _label in KINDS})
    interval = fields.Selection(selection_add=[('hour', 'Hour'), ('minute', 'Minute')], ondelete={'hour': 'set default', 'minute': 'set default'})
    group_ids = fields.Many2many('res.groups', string='Item audience')
    measure2_id = fields.Many2one('ir.model.fields', ondelete='set null')
    extra_measure_ids = fields.Many2many('ir.model.fields', 'td_item_extra_measure_rel', string='Additional measures')
    secondary_as_line = fields.Boolean()
    cumulative_as_line = fields.Boolean()
    comparison_item_id = fields.Many2one('tecnodyne.dashboard.item', string='Second KPI query', ondelete='set null')
    kpi_operation = fields.Selection([('compare', 'Compare'), ('sum', 'Sum'), ('ratio', 'Ratio'), ('percentage', 'Percentage')], default='compare', required=True)
    target_style = fields.Selection([('number', 'Number'), ('progress', 'Progress'), ('both', 'Number and progress')], default='both', required=True)
    tile_style = fields.Selection([('plain', 'Plain'), ('solid', 'Solid color'), ('compact', 'Compact')], default='plain', required=True)
    subgroup_id = fields.Many2one('ir.model.fields', ondelete='set null')
    drill_field_ids = fields.Many2many('ir.model.fields', 'td_item_drill_field_rel', string='Drill hierarchy')
    list_field_ids = fields.Many2many('ir.model.fields', 'td_item_list_field_rel', string='List columns')
    latitude_id = fields.Many2one('ir.model.fields', ondelete='set null')
    longitude_id = fields.Many2one('ir.model.fields', ondelete='set null')
    sort = fields.Selection([('group_asc', 'Group ascending'), ('group_desc', 'Group descending'),
                             ('value_asc', 'Value ascending'), ('value_desc', 'Value descending')], default='group_asc', required=True)
    preset = fields.Selection(PRESETS, default='custom', required=True)
    comparison = fields.Selection([('none', 'None'), ('previous', 'Previous period'), ('year', 'Previous year')], default='none', required=True)
    multiplier = fields.Float(default=1, required=True)
    cumulative = fields.Boolean()
    fill_gaps = fields.Boolean()
    stacked = fields.Boolean()
    show_values = fields.Boolean(default=False)
    show_legend = fields.Boolean(default=True)
    number_format = fields.Selection([('standard', 'Standard'), ('compact', 'Compact'), ('indian', 'Indian'), ('scientific', 'Scientific')], default='standard', required=True)
    currency_id = fields.Many2one('res.currency', string='Display currency')
    icon = fields.Char(default='fa-dashboard')
    color = fields.Char(default='#167d9a')
    target_ids = fields.One2many('tecnodyne.dashboard.target', 'item_id', copy=True)
    task_ids = fields.One2many('tecnodyne.dashboard.task', 'item_id', copy=True)
    client_action_id = fields.Many2one('ir.actions.actions', string='Custom action')

    @api.constrains('kind', 'measure2_id', 'extra_measure_ids', 'subgroup_id', 'list_field_ids', 'drill_field_ids', 'latitude_id', 'longitude_id', 'model_id', 'multiplier', 'color', 'icon', 'comparison_item_id')
    def _validate_features(self):
        import re
        for item in self:
            extra = item.measure2_id | item.extra_measure_ids | item.subgroup_id | item.list_field_ids | item.drill_field_ids | item.latitude_id | item.longitude_id
            for field in extra:
                if field.model_id != item.model_id or not field.store or field.ttype in ('binary', 'html', 'one2many', 'many2many'):
                    raise ValidationError(_('Select stored scalar fields from the source model.'))
            for field in item.measure2_id | item.extra_measure_ids | item.latitude_id | item.longitude_id:
                if field.ttype not in ('integer', 'float', 'monetary'):
                    raise ValidationError(_('A numeric field is required.'))
            if not math.isfinite(item.multiplier) or not re.fullmatch(r'#[0-9a-fA-F]{6}', item.color or ''):
                raise ValidationError(_('Invalid multiplier or color.'))
            if not re.fullmatch(r'fa-[a-z0-9-]+', item.icon or ''):
                raise ValidationError(_('Use a Font Awesome icon name.'))
            if item.kind == 'map' and not (item.latitude_id and item.longitude_id):
                raise ValidationError(_('A map requires latitude and longitude fields.'))
            seen, current = {item.id}, item.comparison_item_id
            while current:
                if current.id in seen or len(seen) > 20:
                    raise ValidationError(_('KPI query references cannot form a cycle.'))
                if current.company_id != item.company_id or current.kind != 'kpi':
                    raise ValidationError(_('The second query must be a KPI in the same company.'))
                seen.add(current.id)
                current = current.comparison_item_id

    def _query(self, date_from=False, date_to=False):
        preset = 'custom' if self.env.context.get('td_comparing') else self.preset if self.preset != 'custom' else self.env.context.get('td_preset', 'custom')
        if preset not in dict(PRESETS):
            raise ValidationError(_('Unknown date range.'))
        if preset != 'custom':
            date_from, date_to = date_range(preset, fields.Date.context_today(self))
        target, domain = super()._query(date_from, date_to)
        visible = target.fields_get()
        for field in self.measure2_id | self.extra_measure_ids | self.subgroup_id | self.list_field_ids | self.drill_field_ids | self.latitude_id | self.longitude_id:
            if field.name not in visible:
                raise AccessError(_('A configured field is restricted.'))
        for filter in self.dashboard_id.filter_ids.filtered(lambda f: f.id in self.env.context.get('td_filters', [])):
            if filter.model_id == self.model_id:
                try:
                    extra = json.loads(filter.domain_json)
                    expression.normalize_domain(extra)
                except (ValueError, TypeError, AssertionError) as exc:
                    raise ValidationError(_('Invalid filter domain.')) from exc
                domain = expression.AND([domain, extra])
        return target, expression.AND([domain, self.env.context.get('td_domain', [])])

    def _convert(self, value):
        return (value or 0) * self.multiplier

    def _aggregate_value(self, target, domain, raw, measure_field=None, aggregation=None):
        measure_field = measure_field or self.measure_id
        aggregation = aggregation or self.aggregation
        if aggregation == 'count' or measure_field.ttype != 'monetary':
            return self._convert(raw)
        destination = self.currency_id or self.company_id.currency_id
        currency_field = target._fields[measure_field.name].currency_field
        if currency_field not in target.fields_get():
            raise AccessError(_('The measure currency field is restricted.'))
        records = target.search(domain, limit=10001)
        if len(records) > 10000:
            raise UserError(_('Currency normalization exceeds 10,000 records. Narrow the date range.'))
        values = []
        for record in records:
            source = record[currency_field] or self.company_id.currency_id
            day = fields.Date.to_date(record[self.date_field_id.name]) if self.date_field_id and record[self.date_field_id.name] else fields.Date.context_today(self)
            values.append(source._convert(record[measure_field.name], destination, self.company_id, day))
        value = {'sum': lambda: sum(values), 'avg': lambda: sum(values)/len(values) if values else 0,
                 'min': lambda: min(values) if values else 0, 'max': lambda: max(values) if values else 0}[aggregation]()
        return self._convert(value)

    def _payload(self, date_from=False, date_to=False, export=False):
        target, domain = self._query(date_from, date_to)
        cap = 10001 if export else self.limit
        page = 0 if export else max(0, min(1000, int(self.env.context.get('td_page', 0))))
        measure = self.measure_id.name if self.aggregation != 'count' else False
        aggregate = measure + ':' + self.aggregation if measure else None
        rows, columns, value, total = [], [], 0, 0
        if self.kind == 'todo':
            tasks = self.env['tecnodyne.dashboard.task'].search([('item_id', '=', self.id)])
            rows = [{'id': task.id, 'label': task.name, 'done': task.done, 'value': int(task.done)} for task in tasks]
        elif self.kind in ('list', 'map'):
            columns = self.list_field_ids.mapped('name') or ['display_name']
            names = list(set(columns + self.latitude_id.mapped('name') + self.longitude_id.mapped('name') + self.measure_id.mapped('name') + self.measure2_id.mapped('name')))
            total = target.search_count(domain)
            records = target.search_read(domain, names, limit=cap, offset=page*cap, order='id ' + ('desc' if self.sort.endswith('desc') else 'asc'))
            for record in records:
                def scalar(v):
                    return v[1] if isinstance(v, tuple) else str(v) if v is not False else ''
                rows.append({'id': record['id'], 'label': str(scalar(record.get(columns[0]))),
                             'cells': [scalar(record.get(n)) for n in columns],
                             'value': self._aggregate_value(target, [('id', '=', record['id'])], record.get(measure, 0)) if measure else 1,
                             'lat': record.get(self.latitude_id.name, 0), 'lon': record.get(self.longitude_id.name, 0),
                             'domain': [('id', '=', record['id'])]})
        elif self.kind == 'kpi':
            value = target.read_group(domain, [aggregate], [], lazy=False)[0].get(measure, 0) if aggregate else target.search_count(domain)
            value = self._aggregate_value(target, domain, value)
        else:
            level = self.env.context.get('td_level', 0)
            grouping = self.group_field_id if not level else self.drill_field_ids.sorted('id')[level-1:level]
            if not grouping:
                raise ValidationError(_('Configure a grouping field.'))
            group = grouping.name + (':' + self.interval if grouping.ttype in ('date', 'datetime') else '')
            subgroup = self.subgroup_id.name + (':' + self.interval if self.subgroup_id.ttype in ('date', 'datetime') else '') if self.subgroup_id else False
            group_fields = [group] + ([subgroup] if subgroup and subgroup != group else [])
            measures = [aggregate] if aggregate else []
            second = self.measure2_id.name
            if second and second != measure:
                measures.append(second + ':sum')
            extra_fields = self.extra_measure_ids.filtered(lambda f: f.name not in (measure, second))
            extra_aggregation = self.aggregation if self.aggregation != 'count' else 'sum'
            measures += [f.name + ':' + extra_aggregation for f in extra_fields]
            order_field = group if self.sort.startswith('group') else measure or 'id'
            order = order_field + (' desc' if self.sort.endswith('desc') else ' asc')
            if not measure and self.sort.startswith('value'):
                order = False
            groups = target.read_group(domain, [g.split(':')[0] for g in group_fields] + measures, group_fields, limit=10001, lazy=False, orderby=order)
            for row in groups:
                label = row.get(group)
                if isinstance(label, tuple):
                    label = label[1]
                sub = row.get(subgroup) if subgroup else ''
                if isinstance(sub, tuple):
                    sub = sub[1]
                # Selection keys are rendered in the current user's language.
                if grouping.ttype == 'selection':
                    label = dict(target.fields_get([grouping.name])[grouping.name]['selection']).get(label, label)
                rows.append({'label': str(label) if label is not False else _('Undefined'), 'series': str(sub or ''),
                             'value': self._aggregate_value(target, row['__domain'], row.get(measure, 0) if measure else row.get('__count', 0)),
                             'value2': self._aggregate_value(target, row['__domain'], row.get(second, 0), self.measure2_id, 'sum') if second else 0, 'domain': row['__domain'],
                             'measures': {f.name: self._aggregate_value(target, row['__domain'], row.get(f.name, 0), f, extra_aggregation) for f in extra_fields},
                             'range': row.get('__range', {}).get(group, {})})
            if not measure and self.sort.startswith('value'):
                rows.sort(key=lambda row: row['value'], reverse=self.sort.endswith('desc'))
            if self.fill_gaps and grouping.ttype in ('date', 'datetime') and not subgroup and rows:
                rows = self._fill_periods(rows, group)
            total = len(rows)
            if self.cumulative or self.cumulative_as_line:
                totals = {}
                for row in rows:
                    series = row.get('series', '')
                    totals[series] = totals.get(series, 0) + row['value']
                    row['cumulative_value'] = totals[series]
                    if self.cumulative:
                        row['value'] = totals[series]
            rows = rows[page*cap:(page+1)*cap]
        if export and len(rows) > 10000:
            raise UserError(_('Export exceeds 10,000 rows. Narrow the filter; no partial export was generated.'))
        for row in rows:
            period = row.get('range', {})
            dated = self.target_ids.filtered(lambda t: period.get('from') and str(t.date) >= str(period['from'])[:10] and str(t.date) < str(period.get('to', '9999-12-31'))[:10])
            row['target'] = sum(dated.mapped('value')) if dated else self.target
        result = {'id': self.id, 'name': self.name, 'kind': self.kind, 'source_kind': self.kind, 'value': value, 'rows': rows,
                  'columns': columns, 'target': self.target, 'page': page, 'total': total, 'unit': (self.currency_id or self.company_id.currency_id).symbol if self.measure_id.ttype == 'monetary' and self.aggregation != 'count' else self.unit or '',
                  'limit': self.limit, 'icon': self.icon, 'color': self.color, 'show_values': self.show_values, 'has_second': bool(self.measure2_id),
                  'secondary_as_line': self.secondary_as_line, 'cumulative_as_line': self.cumulative_as_line,
                  'target_style': self.target_style, 'measure_labels': {f.name: f.field_description for f in self.extra_measure_ids},
                  'tile_style': self.tile_style,
                  'show_legend': self.show_legend, 'stacked': self.stacked, 'number_format': self.number_format,
                  'level': self.env.context.get('td_level', 0), 'depth': len(self.drill_field_ids), 'sequence': self.sequence,
                  'targets': {str(line.date): line.value for line in self.target_ids}}
        if self.kind == 'kpi' and (self.comparison_item_id or self.measure2_id):
            if self.comparison_item_id:
                second_value = self.comparison_item_id.with_context(self.env.context)._payload(date_from, date_to)['value']
            else:
                raw = target.read_group(domain, [self.measure2_id.name+':sum'], [], lazy=False)[0].get(self.measure2_id.name, 0)
                second_value = self._aggregate_value(target, domain, raw, self.measure2_id, 'sum')
            result['second_value'] = second_value
            if self.kpi_operation == 'sum':
                result['value'] = value + second_value
            elif self.kpi_operation in ('ratio', 'percentage'):
                result['value'] = value/second_value * (100 if self.kpi_operation == 'percentage' else 1) if second_value else 0
                result['undefined_ratio'] = not bool(second_value)
                if self.kpi_operation == 'percentage':
                    result['unit'] = '%'
        if self.comparison != 'none' and self.date_field_id and not self.env.context.get('td_comparing'):
            preset = self.preset if self.preset != 'custom' else self.env.context.get('td_preset', 'custom')
            start, end = date_range(preset, fields.Date.context_today(self)) if preset != 'custom' else (fields.Date.to_date(date_from), fields.Date.to_date(date_to))
            if start and end:
                delta = relativedelta(years=1) if self.comparison == 'year' else timedelta(days=(end-start).days+1)
                previous = self.with_context(td_preset='custom', td_comparing=True)
                # _query honors td_comparing to suppress the item's own preset.
                old_target, old_domain = previous._query(start-delta, end-delta)
                old = old_target.read_group(old_domain, [aggregate], [], lazy=False)[0].get(measure, 0) if aggregate else old_target.search_count(old_domain)
                result['previous'] = previous._payload(start-delta, end-delta)['value'] if self.kind == 'kpi' else self._aggregate_value(old_target, old_domain, old)
                current_total = result['value'] if self.kind == 'kpi' else self._aggregate_value(target, domain, target.read_group(domain, [aggregate], [], lazy=False)[0].get(measure, 0) if aggregate else target.search_count(domain))
                result['change'] = ((current_total-result['previous']) / abs(result['previous'])*100) if result['previous'] else None
        return result

    def _comparison_query(self, start, end):
        target, domain = super()._query(start, end)
        return target, expression.AND([domain, self.env.context.get('td_domain', [])])

    def _fill_periods(self, rows, group):
        intervals = {'minute': relativedelta(minutes=1), 'hour': relativedelta(hours=1), 'day': relativedelta(days=1), 'week': relativedelta(weeks=1), 'month': relativedelta(months=1), 'quarter': relativedelta(months=3), 'year': relativedelta(years=1)}
        dated = [row for row in rows if row.get('range', {}).get('from')]
        if not dated or self.interval not in intervals:
            return rows
        by_date = {row['range']['from']: row for row in dated}
        first, last = min(by_date), max(by_date)
        current = fields.Datetime.to_datetime(first)
        end = fields.Datetime.to_datetime(last)
        filled = []
        while current <= end and len(filled) < 10001:
            key = fields.Datetime.to_string(current)
            key_date = str(current.date())
            row = by_date.get(key) or by_date.get(key_date)
            following = current + intervals[self.interval]
            filled.append(row or {'label': key_date, 'series': '', 'value': 0, 'value2': 0,
                                   'domain': [(group.split(':')[0], '>=', key), (group.split(':')[0], '<', fields.Datetime.to_string(following))]})
            current = following
        return filled

    def _path_item(self, path=None, date_from=False, date_to=False, preset='custom', filter_ids=None):
        self.ensure_one()
        if preset not in dict(PRESETS):
            raise ValidationError(_('Unknown date range.'))
        context = dict(self.env.context, td_preset=preset, td_filters=filter_ids or [], td_domain=[], td_level=0)
        item = self.with_context(context)
        for level, index in enumerate(path or []):
            if level >= len(self.drill_field_ids) or type(index) is not int:
                raise ValidationError(_('Invalid drill path.'))
            payload = item._payload(date_from, date_to, export=True)
            if not 0 <= index < len(payload['rows']):
                raise ValidationError(_('Invalid drill group.'))
            item = item.with_context(td_domain=expression.AND([item.env.context['td_domain'], payload['rows'][index]['domain']]), td_level=level+1)
        return item

    def get_item(self, path=None, date_from=False, date_to=False, preset='custom', filter_ids=None):
        return self._path_item(path, date_from, date_to, preset, filter_ids)._payload(date_from, date_to)

    def get_page(self, page=0, path=None, date_from=False, date_to=False, preset='custom', filter_ids=None):
        if type(page) is not int or not 0 <= page <= 1000:
            raise ValidationError(_('Invalid page.'))
        return self._path_item(path, date_from, date_to, preset, filter_ids).with_context(td_page=page)._payload(date_from, date_to)

    def action_drill(self, row_index=False, date_from=False, date_to=False, preset='custom', filter_ids=None, path=None, page=0):
        item = self._path_item(path, date_from, date_to, preset, filter_ids)
        target, domain = item._query(date_from, date_to)
        if row_index is not False:
            rows = item.with_context(td_page=page)._payload(date_from, date_to)['rows']
            if type(row_index) is not int or not 0 <= row_index < len(rows):
                raise ValidationError(_('Invalid group.'))
            domain = rows[row_index].get('domain', domain)
        if self.client_action_id:
            action = self.env[self.client_action_id.type].browse(self.client_action_id.id)
            action.check_access('read')
            return action.read()[0]
        return {'type': 'ir.actions.act_window', 'name': self.name, 'res_model': target._name,
                'views': [(False, 'list'), (False, 'form')], 'domain': domain,
                'context': {'allowed_company_ids': [self.company_id.id]}}

    def action_edit(self):
        self.ensure_one()
        self.check_access('write')
        return {'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': self.id, 'views': [(False, 'form')], 'target': 'new'}

    def action_conversation(self):
        self.ensure_one()
        self.check_access('read')
        return {'type': 'ir.actions.act_window', 'name': self.name, 'res_model': self._name, 'res_id': self.id,
                'views': [(self.env.ref('tecnodyne_dashboard.item_conversation').id, 'form')], 'target': 'new'}

    def action_duplicate(self, dashboard_id=False):
        self.ensure_one()
        self.check_access('read')
        board = self.env['tecnodyne.dashboard'].browse(dashboard_id) if dashboard_id else self.dashboard_id
        board.check_access('write')
        return self.copy({'dashboard_id': board.id}).action_edit()

    def action_move(self, dashboard_id):
        self.ensure_one()
        board = self.env['tecnodyne.dashboard'].browse(dashboard_id)
        board.check_access('write')
        self.write({'dashboard_id': board.id})
        return board.action_open()

    def export_file(self, format='xlsx', date_from=False, date_to=False, preset='custom', filter_ids=None, path=None):
        self.ensure_one()
        data = self._path_item(path, date_from, date_to, preset, filter_ids)._payload(date_from, date_to, export=True)
        if self.kind == 'kpi':
            rows, headers = [[data['name'], data['value']]], [_('Indicator'), _('Value')]
        elif data['columns']:
            rows, headers = [row['cells'] for row in data['rows']], data['columns']
        else:
            extra = list(data['measure_labels'])
            rows = [[row['label'], row.get('series', ''), row['value']] + ([row.get('value2', 0)] if self.measure2_id else []) + [row.get('measures', {}).get(name, 0) for name in extra] for row in data['rows']]
            headers = [_('Group'), _('Series'), _('Value')] + ([_('Second measure')] if self.measure2_id else []) + [data['measure_labels'][name] for name in extra]
        if format == 'csv':
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(headers)
            for row in rows:
                writer.writerow(["'"+v if isinstance(v, str) and v[:1] in '=+-@\t\r' else v for v in row])
            content, mime = ('\ufeff'+output.getvalue()).encode(), 'text/csv'
        elif format == 'xlsx':
            output = io.BytesIO()
            book = xlsxwriter.Workbook(output, {'in_memory': True, 'strings_to_formulas': False, 'strings_to_urls': False})
            sheet = book.add_worksheet('Tecnodyne')
            sheet.write_row(0, 0, headers)
            for index, row in enumerate(rows, 1):
                sheet.write_row(index, 0, row)
            sheet.freeze_panes(1, 0)
            sheet.set_column(0, len(headers)-1, 24)
            book.close()
            content, mime = output.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        else:
            raise ValidationError(_('Unsupported export format.'))
        return {'name': 'tecnodyne-%s.%s' % (self.id, format), 'mime': mime, 'content': base64.b64encode(content).decode()}

    def action_pdf(self, date_from=False, date_to=False, preset='custom', filter_ids=None, path=None, chart_image=False):
        self.ensure_one()
        self.check_access('read')
        if chart_image:
            try:
                raw = base64.b64decode(chart_image, validate=True)
                if len(raw) > 4*1024*1024 or not raw.startswith(b'\x89PNG\r\n\x1a\n'):
                    raise ValueError()
            except (ValueError, TypeError) as exc:
                raise ValidationError(_('Invalid chart image.')) from exc
        return self.env.ref('tecnodyne_dashboard.dashboard_pdf').report_action(self, data={'ids': self.ids, 'date_from': date_from, 'date_to': date_to, 'preset': preset, 'filter_ids': filter_ids or [], 'path': path or [], 'chart_image': chart_image})

    def ai_insight(self, date_from=False, date_to=False, preset='custom', filter_ids=None, path=None):
        self.ensure_one()
        data = self._path_item(path, date_from, date_to, preset, filter_ids)._payload(date_from, date_to)
        # Configured local model only. Aggregate values are intentionally sent to
        # the administrator's inference service, never to Ksolves.
        prompt = 'Explain this dashboard in Spanish. Distinguish observations from hypotheses. Do not invent causes. JSON data: ' + json.dumps(data, default=str)
        return self.env['tecnodyne.dashboard.ai']._generate(prompt)


class Preference(models.Model):
    _name = 'tecnodyne.dashboard.preference'
    _description = 'Personal dashboard layout and favorite'
    dashboard_id = fields.Many2one('tecnodyne.dashboard', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', required=True, default=lambda s: s.env.user, ondelete='cascade')
    layout = fields.Json(default=dict)
    saved_layouts = fields.Json(default=dict)
    favorite = fields.Boolean()
    _sql_constraints = [('unique_preference', 'unique(dashboard_id,user_id)', 'One preference per user and dashboard.')]

    def action_open(self):
        self.ensure_one()
        self.check_access('read')
        return self.dashboard_id.action_open()

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            if not self.env.su and values.get('user_id', self.env.uid) != self.env.uid:
                raise AccessError(_('Personal layouts belong to the current user.'))
            self.env['tecnodyne.dashboard'].browse(values['dashboard_id']).check_access('read')
        return super().create(values_list)

    def write(self, values):
        if not self.env.su and ('user_id' in values or 'dashboard_id' in values):
            raise AccessError(_('The owner and dashboard of a personal layout cannot be changed.'))
        return super().write(values)


class Filter(models.Model):
    _name = 'tecnodyne.dashboard.filter'
    _description = 'Named dashboard filter'
    name = fields.Char(required=True, translate=True)
    dashboard_id = fields.Many2one('tecnodyne.dashboard', required=True, ondelete='cascade')
    model_id = fields.Many2one('ir.model', required=True, ondelete='cascade')
    model_name = fields.Char(related='model_id.model')
    domain_json = fields.Text(default='[]', required=True)

    @api.constrains('domain_json')
    def _check_domain(self):
        for filter in self:
            try:
                domain = json.loads(filter.domain_json)
                if not isinstance(domain, list):
                    raise ValueError()
                expression.normalize_domain(domain)
            except (ValueError, TypeError, AssertionError) as exc:
                raise ValidationError(_('Use a valid JSON filter domain.')) from exc


class Target(models.Model):
    _name = 'tecnodyne.dashboard.target'
    _description = 'Dated dashboard target'
    item_id = fields.Many2one('tecnodyne.dashboard.item', required=True, ondelete='cascade')
    date = fields.Date(required=True)
    value = fields.Float(required=True)


class Task(models.Model):
    _name = 'tecnodyne.dashboard.task'
    _description = 'Dashboard checklist task'
    item_id = fields.Many2one('tecnodyne.dashboard.item', required=True, ondelete='cascade')
    name = fields.Char(required=True)
    done = fields.Boolean()

    def write(self, values):
        if not self.env.user.has_group('tecnodyne_dashboard.group_dashboard_manager') and set(values) != {'done'}:
            raise AccessError(_('Viewers can only complete tasks.'))
        for task in self:
            task.item_id.check_access('read')
        return super().write(values)


class Dataset(models.Model):
    _name = 'tecnodyne.dashboard.dataset'
    _description = 'Imported dashboard data'
    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda s: s.env.company)
    row_ids = fields.One2many('tecnodyne.dashboard.dataset.row', 'dataset_id')


class DatasetRow(models.Model):
    _name = 'tecnodyne.dashboard.dataset.row'
    _description = 'Imported dashboard data row'
    dataset_id = fields.Many2one('tecnodyne.dashboard.dataset', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='dataset_id.company_id', store=True)
    name = fields.Char(required=True)
    category = fields.Char()
    value = fields.Float()
    value2 = fields.Float()
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    amount = fields.Monetary(currency_field='currency_id')
    date = fields.Date()
    latitude = fields.Float()
    longitude = fields.Float()

    @api.constrains('value', 'value2', 'amount', 'latitude', 'longitude')
    def _check_numbers(self):
        for row in self:
            if not all(math.isfinite(row[key]) for key in ('value', 'value2', 'amount', 'latitude', 'longitude')):
                raise ValidationError(_('Imported numbers must be finite.'))
            if not -90 <= row.latitude <= 90 or not -180 <= row.longitude <= 180:
                raise ValidationError(_('Coordinates are outside the valid range.'))


class AI(models.AbstractModel):
    _name = 'tecnodyne.dashboard.ai'
    _description = 'Local Ollama dashboard assistant'

    @api.model
    def _generate(self, prompt, json_mode=False):
        # Only administrators set these parameters. They are not accepted over RPC.
        params = self.env['ir.config_parameter'].sudo()
        url = params.get_param('tecnodyne_dashboard.ollama_url', '')
        model = params.get_param('tecnodyne_dashboard.ollama_model', '')
        if not url or not model:
            raise UserError(_('Configure the Ollama URL and model in Tecnodyne AI settings first.'))
        try:
            payload = {'model': model, 'prompt': prompt, 'stream': False}
            if json_mode:
                payload['format'] = 'json'
            response = requests.post(url.rstrip('/')+'/api/generate', json=payload, timeout=(5, 90), allow_redirects=False)
            response.raise_for_status()
            result = response.json()['response']
            if not isinstance(result, str) or len(result) > 100000:
                raise ValueError()
            return result
        except (requests.RequestException, ValueError, KeyError) as exc:
            raise UserError(_('The AI service did not return a valid response. Check the local model service.')) from exc


class Settings(models.TransientModel):
    _inherit = 'res.config.settings'
    td_ollama_url = fields.Char(config_parameter='tecnodyne_dashboard.ollama_url')
    td_ollama_model = fields.Char(config_parameter='tecnodyne_dashboard.ollama_model')


class PDF(models.AbstractModel):
    _name = 'report.tecnodyne_dashboard.report_dashboard'
    _description = 'Dashboard PDF data'

    def _get_report_values(self, docids, data=None):
        data = data or {}
        items = self.env['tecnodyne.dashboard.item'].browse(docids or data.get('ids', []))
        payloads = [item._path_item(data.get('path', []), data.get('date_from'), data.get('date_to'), data.get('preset', 'custom'), data.get('filter_ids', []))._payload(data.get('date_from'), data.get('date_to'), export=True) for item in items]
        return {'docs': items, 'payloads': payloads, 'doc_ids': items.ids, 'doc_model': items._name, 'chart_image': data.get('chart_image')}
