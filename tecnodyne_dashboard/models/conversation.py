from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class DashboardChannel(models.Model):
    _inherit = 'discuss.channel'

    td_item_id = fields.Many2one('tecnodyne.dashboard.item', ondelete='cascade', index=True, copy=False)
    _sql_constraints = [('td_unique_item_channel', 'unique(td_item_id)', 'One conversation per indicator.')]

    def _td_allowed_partner(self, partner):
        self.ensure_one()
        item = self.td_item_id.sudo()
        for user in partner.sudo().user_ids.filtered(lambda u: u.active and not u.share):
            if (item.company_id in user.company_ids
                    and user.has_group('tecnodyne_dashboard.group_dashboard_user')
                    and (not item.group_ids or bool(item.group_ids & user.groups_id))
                    and (not item.dashboard_id.group_ids or bool(item.dashboard_id.group_ids & user.groups_id))):
                return True
        return False

    def add_members(self, partner_ids=None, guest_ids=None, **kwargs):
        for channel in self.filtered('td_item_id'):
            channel.td_item_id.check_access('read')
            if guest_ids or any(not channel._td_allowed_partner(p) for p in self.env['res.partner'].browse(partner_ids or [])):
                raise AccessError(_('Only authorized dashboard viewers can join this conversation.'))
        return super().add_members(partner_ids=partner_ids, guest_ids=guest_ids, **kwargs)

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        for channel in self.filtered('td_item_id'):
            # Remove revoked viewers before delivering any new content through bus.
            stale = channel.sudo().channel_member_ids.filtered(lambda m: not m.partner_id or not channel._td_allowed_partner(m.partner_id))
            stale.unlink()
        return super()._notify_thread(message, msg_vals=msg_vals, **kwargs)

    def write(self, values):
        if 'td_item_id' in values and not self.env.su:
            raise AccessError(_('Dashboard conversation links cannot be changed.'))
        return super().write(values)


class ItemConversation(models.Model):
    _inherit = 'tecnodyne.dashboard.item'

    def action_conversation(self):
        self.ensure_one()
        self.check_access('read')
        channel = self.env['discuss.channel'].sudo().search([('td_item_id', '=', self.id)], limit=1)
        if not channel:
            channel = self.env['discuss.channel'].sudo().create({'name': 'Tecnodyne · '+self.name,
                'channel_type': 'group', 'td_item_id': self.id,
                'channel_partner_ids': [(4, self.env.user.partner_id.id)]})
        # Membership is granted only after checking the indicator's rules.
        channel.with_user(self.env.user).add_members(partner_ids=[self.env.user.partner_id.id], post_joined_message=False)
        return {'type': 'ir.actions.act_url', 'url': '/odoo/discuss?active_id=discuss.channel_%s' % channel.id, 'target': 'self'}
