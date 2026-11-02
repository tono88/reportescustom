from odoo import api, models


class WatchedItems(models.Model):
    _inherit = 'tecnodyne.dashboard.item'

    def _register_hook(self):
        result = super()._register_hook()
        self.env.registry._tecnodyne_watched_models = frozenset(self.sudo().search([]).mapped('model_name'))
        return result

    def _refresh_watches(self):
        self.env.registry._tecnodyne_watched_models = frozenset(self.sudo().search([]).mapped('model_name'))

    @api.model_create_multi
    def create(self, values_list):
        result = super().create(values_list)
        result._refresh_watches()
        return result

    def write(self, values):
        result = super().write(values)
        self._refresh_watches()
        return result

    def unlink(self):
        result = super().unlink()
        self._refresh_watches()
        return result


class SourceEvents(models.AbstractModel):
    _inherit = 'base'

    def _td_notify(self):
        if self._name in getattr(self.env.registry, '_tecnodyne_watched_models', ()):
            # No record IDs, company IDs or values leave this method. Bus commits
            # with the transaction, then each client re-queries with its own ACL.
            self.env['bus.bus']._sendone('tecnodyne_dashboard_updates', 'tecnodyne_dashboard_changed', {'model': self._name})

    @api.model_create_multi
    def create(self, values_list):
        result = super().create(values_list)
        result._td_notify()
        return result

    def write(self, values):
        result = super().write(values)
        self._td_notify()
        return result

    def _write(self, values):
        result = super()._write(values)
        # Stored computed values can flush without passing through write().
        self._td_notify()
        return result

    def unlink(self):
        self._td_notify()
        return super().unlink()
