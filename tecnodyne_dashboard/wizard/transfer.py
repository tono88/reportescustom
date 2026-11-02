import json
from odoo import fields, models, _
from odoo.exceptions import ValidationError


class Transfer(models.TransientModel):
    _name = 'tecnodyne.dashboard.transfer'
    _description = 'Dashboard JSON transfer'

    dashboard_id = fields.Many2one('tecnodyne.dashboard')
    document = fields.Text(string='JSON configuration')

    def action_export(self):
        self.ensure_one()
        board = self.dashboard_id
        if not board:
            raise ValidationError(_('Select a dashboard.'))
        board.check_access('read')
        items = []
        for item in board.item_ids:
            item.check_access('read')
            values = {key: item[key] for key in self._keys()}
            values['model'] = item.model_name
            for key in ('measure_id', 'group_field_id', 'date_field_id'):
                values[key] = item[key].name or False
            items.append(values)
        self.document = json.dumps({'schema': 1, 'name': board.name, 'items': items}, ensure_ascii=False, indent=2)
        return self._reopen()

    def _keys(self):
        return ('name', 'sequence', 'kind', 'aggregation', 'interval', 'domain_json', 'limit', 'target', 'unit')

    def action_import(self):
        self.ensure_one()
        try:
            data = json.loads(self.document or '')
            if data['schema'] != 1 or not isinstance(data['items'], list) or len(data['items']) > 100:
                raise ValueError()
            commands = []
            for raw in data['items']:
                model = self.env['ir.model'].search([('model', '=', raw['model'])], limit=1)
                if not model:
                    raise ValueError()
                values = {key: raw[key] for key in self._keys() if key in raw}
                values['model_id'] = model.id
                for key in ('measure_id', 'group_field_id', 'date_field_id'):
                    field = self.env['ir.model.fields'].search([('model_id', '=', model.id), ('name', '=', raw.get(key))], limit=1) if raw.get(key) else False
                    if raw.get(key) and not field:
                        raise ValueError()
                    values[key] = field.id if field else False
                commands.append((0, 0, values))
            board = self.env['tecnodyne.dashboard'].create({'name': data['name'], 'item_ids': commands})
        except (ValueError, KeyError, TypeError) as exc:
            raise ValidationError(_('Invalid or incompatible configuration. Install the required source modules first.')) from exc
        return board.action_open()

    def _reopen(self):
        return {'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': self.id,
                'views': [(False, 'form')], 'target': 'new'}
