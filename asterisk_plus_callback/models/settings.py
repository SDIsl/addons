from odoo import models, fields


class CallbackSettings(models.Model):
    _inherit = 'asterisk_plus.settings'

    callback_not_after = fields.Char(default='18:00', string='Not After')
    callback_not_before = fields.Char(default='08:00', string='Not Before')
    # Callback interval in minutes
    callback_attempt_interval = fields.Integer(default=1, string='Attempt Interval')
    callback_daily_attempts = fields.Integer(default=3, string='Daily Attempts')
    callback_max_attempts = fields.Integer(default=9, string='Max Attempts')
