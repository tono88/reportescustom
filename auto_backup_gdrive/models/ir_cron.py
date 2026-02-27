# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

from odoo import _, fields, models
from odoo.exceptions import UserError


class IrCron(models.Model):
    _inherit = 'ir.cron'

    db_auto_backup_rule = fields.Many2one('db.auto.backup.rule')

    def unlink(self):
        if self.db_auto_backup_rule.exists() and not self.env.context.get('force_backup_unlink'):
            raise UserError(_("You can not delete this scheduled action as it is used in db backup rule."))
        return super(IrCron, self).unlink()
