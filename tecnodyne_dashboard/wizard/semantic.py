import hashlib
import json
import math
import re
import unicodedata

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text or '') if not unicodedata.combining(c)).lower()


class SemanticGeneration(models.TransientModel):
    _inherit = 'tecnodyne.dashboard.generate'

    model_id = fields.Many2one(required=False)
    source_mode = fields.Selection([('auto', 'Resolve business source'), ('manual', 'Use selected model')], default='auto', required=True)
    sales_channel = fields.Selection([('both', 'Sales and POS separately'), ('sale', 'Sales orders'), ('pos', 'Point of sale')], default='both', required=True)
    sales_metric = fields.Selection([('auto', 'Detect from request'), ('quantity', 'Net quantity'), ('amount', 'Untaxed sales amount')], default='auto', required=True)
    top_limit = fields.Integer(default=10, required=True)
    plan_explanation = fields.Text(readonly=True)
    proposal_engine = fields.Selection([('business', 'Validated business plan'), ('ai', 'Local AI proposal')], readonly=True)
    proposal_fingerprint = fields.Char(readonly=True)
    analysis_preset = fields.Selection([('custom', 'Consulta propia'), ('categories', 'Categorías más vendidas por mes'),
        ('products', 'Productos más vendidos por mes'), ('trend', 'Tendencia mensual de ventas'),
        ('cash', 'Saldo contable de efectivo y bancos'), ('cash_flow', 'Flujo neto de efectivo por contacto'),
        ('profit', 'Resultado contable por mes'), ('expenses', 'Gastos por cuenta y mes'),
        ('payables', 'Cuentas por pagar a proveedores')], default='custom', required=True, string='Análisis predefinido')

    @api.onchange('analysis_preset')
    def _set_preset_request(self):
        phrases = {'categories': 'Categorías de productos más vendidas por mes', 'products': 'Productos más vendidos por mes',
                   'trend': 'Tendencia de ventas por mes en importe', 'cash': 'Ver liquidez en efectivo y bancos',
                   'cash_flow': 'Flujo de efectivo por contacto', 'profit': 'Pérdidas y ganancias por mes',
                   'expenses': 'Gastos por cuenta por mes', 'payables': 'Cuentas por pagar a proveedores'}
        if self.analysis_preset in phrases:
            self.keywords = phrases[self.analysis_preset]
        self._invalidate_proposal()

    @api.constrains('top_limit')
    def _check_top_limit(self):
        if any(not 1 <= wizard.top_limit <= 100 for wizard in self):
            raise ValidationError(_('Top limit must be between 1 and 100.'))

    @api.onchange('model_id', 'keywords', 'item_count', 'dashboard_id', 'source_mode', 'sales_channel', 'sales_metric', 'top_limit', 'analysis_preset')
    def _invalidate_proposal(self):
        self.proposal = False
        self.proposal_fingerprint = False
        self.plan_explanation = False
        self.proposal_engine = False

    def _request_fingerprint(self):
        self.ensure_one()
        request = [self.model_id.id, self.keywords, self.item_count, self.dashboard_id.id,
                   self.source_mode, self.sales_channel, self.sales_metric, self.top_limit, self.analysis_preset]
        return hashlib.sha256(json.dumps(request, ensure_ascii=False).encode()).hexdigest()

    def _sales_intent(self):
        text = normalized(self.keywords)
        sales = bool(re.search(r'vendid|ventas?|selling|sales|sold', text))
        dimension = 'category' if re.search(r'categor|familia', text) else 'product' if re.search(r'producto|products?', text) else False
        if sales and not dimension and re.search(r'tendencia|trend|\bmes\b|mensual|months?', text):
            dimension = 'date'
        if not sales or not dimension:
            return False
        monthly = bool(re.search(r'\bmes\b|mensual|meses|months?', text))
        metric = self.sales_metric
        if metric == 'auto':
            metric = 'amount' if dimension == 'date' or re.search(r'import|monto|ingres|factur|revenue|amount|valor monet', text) else 'quantity'
        top = self.top_limit
        match = re.search(r'\b(?:top|primer[ao]s?|mejores)\s+(\d+)\b', text)
        if match:
            top = min(100, max(1, int(match.group(1))))
        return {'dimension': dimension, 'monthly': monthly, 'metric': metric, 'top': top}

    def _finance_intent(self):
        text = normalized(self.keywords)
        monthly = bool(re.search(r'\bmes\b|mensual|meses|months?', text))
        if re.search(r'flujo.*efectivo|cash.?flow', text):
            return {'topic': 'cash_flow', 'monthly': monthly, 'partner': bool(re.search(r'cliente|proveedor|partner|contact', text))}
        if re.search(r'liquidez|efectivo|saldo.*(?:caja|banco)|cash balance|bank balance', text):
            return {'topic': 'cash_balance', 'monthly': monthly}
        if re.search(r'perdidas.*ganancias|profit.*loss|utilidad|resultado contable', text):
            return {'topic': 'profit_loss', 'monthly': monthly}
        if re.search(r'cuentas por pagar|vendor payables|deuda.*proveedor|saldo.*proveedor', text):
            return {'topic': 'payables', 'monthly': monthly}
        if re.search(r'patron.*gasto|gastos por|expense pattern|expenses by', text):
            return {'topic': 'expenses', 'monthly': monthly}
        return False

    def _catalog_intent(self):
        financial = self._finance_intent()
        if financial:
            return dict(financial, family='finance')
        sales = self._sales_intent()
        return dict(sales, family='sales') if sales else False

    def _finance_items(self, intent):
        target = self._source_target('account.move.line')
        fields_meta = target.fields_get()
        required = ('balance', 'date', 'account_id', 'parent_state')
        if any(name not in fields_meta for name in required):
            raise UserError(_('The authorized accounting source cannot supply this analysis.'))
        posted = [['parent_state', '=', 'posted']]
        cash = posted + [['account_id.account_type', '=', 'asset_cash']]
        company = self.dashboard_id.company_id if self.dashboard_id else self.env.company
        common = {'model': target._name, 'aggregation': 'sum', 'measure': 'balance', 'date': 'date',
                  'interval': 'month', 'sort': 'group_asc', 'unit': company.currency_id.symbol,
                  'domain': posted, 'kind': 'line' if intent['monthly'] else 'kpi'}
        if intent['topic'] == 'cash_balance' and intent['monthly']:
            query = """WITH RECURSIVE
            bounds AS (SELECT date(MIN(date),'start of month') first_month,
                date(COALESCE(:date_to,date('now')),'start of month') last_month FROM ledger),
            months(month) AS (SELECT first_month FROM bounds WHERE first_month IS NOT NULL
                UNION ALL SELECT date(month,'+1 month') FROM months,bounds WHERE month < last_month),
            movement AS (SELECT date(date,'start of month') month,SUM(balance) amount FROM ledger GROUP BY 1),
            balances AS (SELECT months.month,SUM(COALESCE(movement.amount,0)) OVER
                (ORDER BY months.month ROWS UNBOUNDED PRECEDING) value FROM months LEFT JOIN movement USING(month))
            SELECT month AS label,value FROM balances
                WHERE :date_from IS NULL OR month >= date(:date_from,'start of month') ORDER BY month"""
            return [dict(common, name=_('Posted cash and bank balance at month end'), query_mode='sql',
                         query_sql=query, query_sources=[{'alias': 'ledger', 'model': target._name,
                            'fields': ['balance', 'date'], 'date_field': 'date', 'date_scope': 'as_of',
                            'domain_json': json.dumps(cash)}])]
        if intent['topic'] == 'cash_balance':
            return [dict(common, name=_('Posted cash and bank book balance'), date_scope='as_of', domain=cash)]
        if intent['topic'] == 'cash_flow':
            return [dict(common, name=_('Posted net cash movement'), domain=cash,
                         kind='bar', group='date' if intent['monthly'] else 'partner_id' if intent.get('partner') else 'account_id',
                         subgroup='partner_id' if intent['monthly'] and intent.get('partner') else None)]
        if intent['topic'] == 'profit_loss':
            domain = posted + [['account_id.account_type', 'in', ['income', 'income_other', 'expense', 'expense_direct_cost', 'expense_depreciation']]]
            return [dict(common, name=_('Posted income less expenses'), domain=domain, multiplier=-1,
                         group='date' if intent['monthly'] else None)]
        if intent['topic'] == 'expenses':
            domain = posted + [['account_id.account_type', 'in', ['expense', 'expense_direct_cost', 'expense_depreciation']]]
            return [dict(common, name=_('Posted expense pattern'), kind='bar', domain=domain,
                         group='account_id', subgroup='date' if intent['monthly'] else None)]
        if intent['topic'] == 'payables':
            if 'amount_residual' not in fields_meta or 'date_maturity' not in fields_meta:
                raise UserError(_('The source does not expose current residual amounts and maturity dates.'))
            domain = posted + [['account_id.account_type', '=', 'liability_payable'], ['amount_residual', '!=', 0]]
            return [dict(common, name=_('Current open supplier balance by maturity'), kind='bar',
                         measure='amount_residual', multiplier=-1, domain=domain, date='date_maturity',
                         group='partner_id', subgroup='date_maturity' if intent['monthly'] else None)]
        raise UserError(_('This accounting analysis has no validated recipe.'))

    def _catalog_items(self, intent):
        return self._finance_items(intent) if intent['family'] == 'finance' else self._business_items(intent)

    def _source_target(self, name):
        if name not in self.env:
            raise UserError(_('Source model %s is not installed. Install its application or choose another sales channel.', name))
        company = self.dashboard_id.company_id if self.dashboard_id else self.env.company
        if self.dashboard_id:
            self.dashboard_id.check_access('write')
        if company not in self.env.companies:
            raise UserError(_('Select the dashboard company in the company selector.'))
        target = self.env[name].with_context(allowed_company_ids=[company.id])
        target.check_access('read')
        return target

    def _business_items(self, intent):
        channels = ['sale', 'pos'] if self.sales_channel == 'both' else [self.sales_channel]
        if self.item_count < len(channels):
            raise UserError(_('Choose at least two indicators for separate Sales and POS charts.'))
        specs = []
        for channel in channels:
            source = 'sale.report' if channel == 'sale' else 'report.pos.order'
            target = self._source_target(source)
            group = 'date' if intent['dimension'] == 'date' else ('categ_id' if channel == 'sale' else 'product_categ_id') if intent['dimension'] == 'category' else 'product_id'
            measure = ('product_uom_qty' if channel == 'sale' else 'product_qty') if intent['metric'] == 'quantity' else ('price_subtotal' if channel == 'sale' else 'price_subtotal_excl')
            visible = target.fields_get()
            required = [measure, group, 'date', 'state', 'company_id']
            if any(name not in visible or not target._fields[name].store for name in required):
                raise UserError(_('The sales source lacks an authorized stored field required by this plan: %s', source))
            states = ['sale'] if channel == 'sale' else ['paid', 'done', 'invoiced']
            dimension = _('Sales trend') if intent['dimension'] == 'date' else _('Categories') if intent['dimension'] == 'category' else _('Products')
            channel_label = _('Sales orders') if channel == 'sale' else _('POS')
            metric_label = _('net quantity') if intent['metric'] == 'quantity' else _('untaxed amount')
            specs.append({'model': source, 'name': '%s — %s (%s)' % (dimension, channel_label, metric_label),
                          'kind': 'bar', 'aggregation': 'sum', 'measure': measure, 'group': group,
                          'subgroup': 'date' if intent['monthly'] and intent['dimension'] != 'date' else None, 'date': 'date',
                          'interval': 'month', 'sort': 'group_asc' if intent['dimension'] == 'date' else 'value_desc',
                          'top_n_per_period': intent['top'] if intent['monthly'] and intent['dimension'] != 'date' else 0,
                          'limit': 200 if intent['monthly'] else intent['top'],
                          'unit': _('Product base units') if intent['metric'] == 'quantity' else (self.dashboard_id.company_id if self.dashboard_id else self.env.company).currency_id.symbol,
                          'domain': [['state', 'in', states], [group, '!=', False]]})
        return specs

    def _allowed_sources(self):
        intent = self._catalog_intent()
        if self.source_mode == 'auto' and intent:
            return {spec['model'] for spec in self._catalog_items(intent)}
        if not self.model_id:
            raise UserError(_('Select a source model for this request.'))
        return {self.model_id.model}

    def _check_request_contract(self, spec, source):
        text = normalized(self.keywords)
        explicit_count = bool(re.search(r'conteo|contar|\bcount\b|cuantos|cuantas|numero de|cantidad de (?:contactos|clientes|usuarios|empleados|registros|documentos)', text))
        if spec['aggregation'] == 'count' and not explicit_count:
            raise ValidationError(_('This request is not a record count. The generated count was rejected; choose an appropriate source or refine the requested measure.'))
        if spec.get('query_mode') != 'sql' and re.search(r'\bmes\b|mensual|meses|months?', text):
            if not spec.get('date') or spec.get('interval', 'month') != 'month' or spec.get('date') not in (spec.get('group'), spec.get('subgroup')):
                raise ValidationError(_('A monthly request requires grouping by its date field by month. A flat KPI does not answer it.'))
        intent = self._catalog_intent()
        if intent:
            expected = {item['model']: item for item in self._catalog_items(intent)}
            if source not in expected:
                raise ValidationError(_('The selected source describes products or categories, not sales transactions. Use automatic business-source resolution.'))
            correct = expected[source]
            for key in ('aggregation', 'measure', 'group', 'subgroup', 'date', 'interval', 'top_n_per_period', 'date_scope', 'multiplier', 'query_mode', 'query_sql', 'query_sources'):
                if key not in correct:
                    continue
                if spec.get(key, 'month' if key == 'interval' else 0 if key == 'top_n_per_period' else None) != correct.get(key):
                    raise ValidationError(_('The proposal does not match the requested sales measure, category or monthly grouping.'))
            if spec.get('domain', []) != correct['domain']:
                raise ValidationError(_('Sales plans must exclude draft and cancelled transactions.'))

    def action_generate(self):
        self.ensure_one()
        self.check_access('write')
        intent = self._catalog_intent()
        if self.source_mode == 'auto' and intent:
            specs = self._catalog_items(intent)
            raw = json.dumps({'items': specs}, ensure_ascii=False)
            engine = 'business'
            explanation = _('Validated sales plan: quantities or untaxed amounts, confirmed transactions only, separate channels. Monthly Top N is calculated inside each month. Quantities use product base units; do not compare incompatible units of measure.') if intent['family'] == 'sales' else _('Validated posted-ledger plan. Cash balances include opening history through the end date; cash movements use the selected range. Supplier residuals represent current outstanding amounts, grouped by maturity, not a historical aging reconstruction.')
        else:
            if intent:
                raise UserError(_('Choose automatic business-source resolution for this analysis; a generic model selection does not define its transactional measure.'))
            if not self.model_id:
                raise UserError(_('Select a source model or request a supported business analysis.'))
            target = self._source_target(self.model_id.model)
            schema = {n: {'type': f['type'], 'label': f['string']} for n, f in target.fields_get().items()
                      if target._fields[n].store and f['type'] in ('char', 'selection', 'many2one', 'date', 'datetime', 'integer', 'float', 'monetary')}
            prompt = (f'Build up to {self.item_count} Odoo dashboard items that answer the user request. Do not substitute a record count for an analysis. '
                      'Return JSON {"items":[...]}, or {"items":[]} if the source cannot answer it. Each item has name, kind (kpi/bar/line/pie/table), '
                      'aggregation (sum/avg/count), measure (numeric field or null for count), group (field or null for KPI), subgroup (field or null), '
                      'date (date field or null), interval (day/week/month/quarter/year), sort (group_asc/group_desc/value_asc/value_desc), domain (Odoo JSON domain). '
                      'A request by month must group or subgroup by the date field, interval month. Field names must exist in the supplied schema. '
                      'Only use count when explicitly requested. Do not invent financial meanings or relationships. Return JSON null rather than "null". '
                      + 'Request: '+self.keywords+'\nModel: '+target._name+'\nSchema: '+json.dumps(schema, ensure_ascii=False))
            raw = self.env['tecnodyne.dashboard.ai']._generate(prompt, json_mode=True)
            engine, explanation = 'ai', _('Local AI proposal; source, measures and requested grouping are checked before application. Review the query and business meaning.')
        self._validated_items(raw)
        self.write({'proposal': raw, 'proposal_fingerprint': self._request_fingerprint(),
                    'proposal_engine': engine, 'plan_explanation': explanation})
        return {'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': self.id, 'views': [(False, 'form')], 'target': 'new'}

    def _validated_items(self, raw):
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and data.get('items') == []:
                raise UserError(_('The selected source cannot answer this request. Select a source containing the requested transactions, measures and dates. No fallback count was created.'))
            if not isinstance(data, dict) or not isinstance(data.get('items'), list) or not 1 <= len(data['items']) <= self.item_count:
                raise ValueError()
            allowed = self._allowed_sources()
            commands = []
            for spec in data['items']:
                source = spec.get('model') or self.model_id.model
                if source not in allowed:
                    raise ValueError()
                target = self._source_target(source)
                visible = target.fields_get()
                if spec['kind'] not in ('kpi', 'bar', 'line', 'pie', 'table') or spec['aggregation'] not in ('count', 'sum', 'avg'):
                    raise ValueError()
                self._check_request_contract(spec, source)
                values = {'name': str(spec['name'])[:150], 'model_id': self.env['ir.model']._get_id(source),
                          'kind': spec['kind'], 'aggregation': spec['aggregation'], 'domain_json': json.dumps(spec.get('domain', []))}
                if spec.get('query_mode') == 'sql':
                    if not self._catalog_intent():
                        raise ValueError()
                    values.update(query_mode='sql', query_sql=spec['query_sql'])
                    sources = []
                    for sql_source in spec['query_sources']:
                        sql_target = self._source_target(sql_source['model'])
                        allowed_fields = sql_target.fields_get()
                        if any(name not in allowed_fields for name in sql_source['fields']):
                            raise ValueError()
                        sources.append((0, 0, {'alias': sql_source['alias'], 'model_id': self.env['ir.model']._get_id(sql_target._name),
                            'field_ids': [(6, 0, [self.env['ir.model.fields']._get(sql_target._name, name).id for name in sql_source['fields']])],
                            'date_field_id': self.env['ir.model.fields']._get(sql_target._name, sql_source['date_field']).id,
                            'date_scope': sql_source.get('date_scope', 'range'), 'domain_json': sql_source['domain_json']}))
                    values['query_source_ids'] = sources
                    values['unit'] = spec.get('unit', '')
                    commands.append((0, 0, values))
                    continue
                domain = spec.get('domain', [])
                if not isinstance(domain, list):
                    raise ValueError()
                expression.normalize_domain(domain)
                for leaf in domain:
                    if isinstance(leaf, (list, tuple)) and (len(leaf) != 3 or leaf[0].split('.')[0] not in visible):
                        raise ValueError()
                for key, field_name in [('measure', 'measure_id'), ('group', 'group_field_id'), ('subgroup', 'subgroup_id'), ('date', 'date_field_id')]:
                    name = spec.get(key)
                    if name and (name not in visible or not target._fields[name].store):
                        raise ValueError()
                    if key == 'measure' and spec['aggregation'] != 'count' and (not name or visible[name]['type'] not in ('integer', 'float', 'monetary')):
                        raise ValueError()
                    if key in ('group', 'subgroup') and (key == 'group' and spec['kind'] != 'kpi' and not name or name and visible[name]['type'] not in ('many2one', 'char', 'selection', 'boolean', 'date', 'datetime', 'integer')):
                        raise ValueError()
                    if key == 'date' and name and visible[name]['type'] not in ('date', 'datetime'):
                        raise ValueError()
                    values[field_name] = self.env['ir.model.fields']._get(source, name).id if name else False
                for key in ('interval', 'sort', 'limit', 'top_n_per_period', 'unit', 'multiplier', 'date_scope'):
                    value = spec.get(key)
                    # Models may send null for settings irrelevant to a KPI.
                    # Preserve required Odoo defaults instead of writing SQL NULL.
                    if value is None:
                        continue
                    field = self.env['tecnodyne.dashboard.item']._fields[key]
                    if field.type == 'selection' and value not in field.get_values(self.env):
                        raise ValueError()
                    if key in ('limit', 'top_n_per_period') and (type(value) is not int or not (1 if key == 'limit' else 0) <= value <= (200 if key == 'limit' else 100)):
                        raise ValueError()
                    if key == 'multiplier' and (type(value) not in (int, float) or not math.isfinite(value)):
                        raise ValueError()
                    values[key] = value
                commands.append((0, 0, values))
            return commands
        except (ValueError, TypeError, KeyError, AssertionError, AttributeError) as exc:
            raise ValidationError(_('The AI proposal is incompatible with the authorized source or request. No indicator was created.')) from exc

    def action_apply(self):
        self.ensure_one()
        self.check_access('write')
        if not self.proposal or self.proposal_fingerprint != self._request_fingerprint():
            raise UserError(_('The request or source changed. Generate and review a new proposal before applying it.'))
        commands = self._validated_items(self.proposal)
        board = self.dashboard_id
        if board:
            board.write({'item_ids': commands})
        else:
            board = self.env['tecnodyne.dashboard'].create({'name': self.name, 'item_ids': commands})
        return board.action_open()
