import json
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from .server import debug

logger = logging.getLogger(__name__)


class ChannelMessage(models.Model):
    _name = 'asterisk_plus.channel_message'
    _rec_name = 'uniqueid'
    _order = 'id desc'
    _description = 'Channel Message'

    channel_id = fields.Many2one('asterisk_plus.channel', ondelete='cascade')
    event = fields.Char(index=True, size=64)
    privilege = fields.Char(size=256)
    channel = fields.Char(index=True, size=256)
    uniqueid = fields.Char(size=150, index=True, string='Unique ID')
    context = fields.Char(size=80)
    exten = fields.Char(size=32)
    callerid_num = fields.Char(size=32, string='CallerID number')
    callerid_name = fields.Char(size=32, string='CallerID name')
    system_name = fields.Char(size=128)
    message = fields.Text()

    @api.model
    def create_from_event(self, channel, event):
        data = {
            'channel_id': channel.id,
            'event': event['Event'],
            'channel': event['Channel'],
            'callerid_num': event['CallerIDNum'],
            'callerid_name': event['CallerIDName'],
            'context': event['Context'],
            'exten': event['Exten'],
            'uniqueid': event['Uniqueid'],
            'message': json.dumps(event, indent=2),

        }
        self.create(data)

