# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2021
from datetime import datetime, timedelta
import json
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from .server import debug

logger = logging.getLogger(__name__)

class Call(models.Model):
    _name = 'asterisk_plus.call'
    _description = 'Asterisk Call'
    _order = 'id desc'
    _log_access = False
    _rec_name = 'id'

    uniqueid = fields.Char(size=64, index=True)
    server = fields.Many2one('asterisk_plus.server', ondelete='cascade')
    calling_number = fields.Char(index=True)
    called_number = fields.Char(index=True)
    started = fields.Datetime(index=True)
    answered = fields.Datetime(index=True)
    ended = fields.Datetime(index=True)
    direction = fields.Selection(selection=[('in', 'Incoming'), ('out', 'Outgoing')],
        index=True, size=3)
    direction_icon = fields.Html(string='<->', compute='_get_direction_icon')
    status = fields.Selection(selection=[
         ('noanswer', 'No Answer'), ('answered', 'Answered'),
         ('busy', 'Busy'), ('failed', 'Failed'),
         ('progress', 'In Progress')], index=True, default='progress',
         size=8)
    # Boolean index for split all calls on this flag.
    is_active = fields.Boolean(index=True)
    channels = fields.One2many('asterisk_plus.channel', inverse_name='call')
    partner = fields.Many2one('res.partner', ondelete='set null')
    calling_user = fields.Many2one('res.users', ondelete='set null')
    called_user = fields.Many2one('res.users', ondelete='set null')

    def _get_direction_icon(self):
        for rec in self:
            rec.direction_icon = '<span class="arrow-left"/>' if rec.direction == 'in' else \
                '<span class="arrow-right"/>'

    def _get_call_users(self):
        for rec in self:
            user_channel = self.env['asterisk_plus.user_channel'].get_user_channel(
                rec.channel, rec.system_name)
            if user_channel:
                if user_channel.originate_context == rec.context:
                    debug(self, 'Src user: {}'.format(user_channel.sudo().asterisk_user.user.name))
                    rec.src_user = user_channel.sudo().asterisk_user.user.id
                    if rec.parent_channel.dst_user:
                        rec.dst_user = rec.parent_channel.dst_user
                    else:
                        rec.dst_user = False
                else:
                    debug(self, 'Dst user: {}'.format(user_channel.sudo().asterisk_user.user.name))
                    rec.dst_user = user_channel.sudo().asterisk_user.user.id
                    if rec.parent_channel.src_user:
                        rec.src_user = rec.parent_channel.src_user
                    else:
                        rec.src_user = False
            else:
                rec.src_user = False
                rec.dst_user = False

    def reload_calls(self, data={}):
        # TODO:
        self.ensure_one()
        msg = {
            'event': 'update_channel',
            'dst': self.exten,
            'system_name': self.system_name,
            'channel': self.channel_short,
            'auto_reload': True
        }
        if self.partner:
            msg.update(res_id=self.partner.id, model='res.partner')
        msg.update(data)
        self.env['bus.bus'].sendone('asterisk_plus_channels', json.dumps(msg))

    def move_to_history(self):
        self.is_active = False
