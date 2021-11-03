import logging
from odoo import models, fields, api, tools, release, _
from odoo.exceptions import ValidationError, UserError
from .server import get_default_server

logger = logging.getLogger(__name__)


class ResUser(models.Model):
    _inherit = 'res.users'

    asterisk_users = fields.One2many(
        'asterisk_plus.user', inverse_name='user')
    # Used from channels.js
    calls_open_partner_form = fields.Boolean(default=True)

    @api.model
    def asterisk_plus_notify(self, message, title='PBX', uid=None,
                             sticky=False, warning=False):
        """Send a notification to logged in Odoo user.

        Args:
            message (str): Notification message.
            title (str): Notification title. If not specified: PBX.
            uid (int): Odoo user UID to send notification to. If not specified: calling user UID.
            sticky (boolean): Make a notiication message sticky (shown until closed). Default: False.
            warning (boolean): Make a warning notification type. Default: False.
        Returns:
            Always True.
        """
        # Use calling user UID if not specified.
        if not uid:
            uid = self.env.uid
        self.env['bus.bus'].sendone(
            'asterisk_plus_notification_{}'.format(uid),
            {
                'message': message,
                'title': title,
                'sticky': sticky,
                'warning': warning
            })
        return True

    @api.model
    def get_asterisk_channels(self, uid):
        # Used from channels.js
        res = {}
        user_channels = self.env['asterisk_plus.user_channel'].search(
            [('user', '=', uid)])
        for user_channel in user_channels:
            res.setdefault(
                user_channel.system_name, []).append(user_channel.name)
        return res
