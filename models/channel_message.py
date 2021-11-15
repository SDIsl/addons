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
    linkedid = fields.Char(size=150, index=True, string='Linked ID')
    context = fields.Char(size=80)
    connected_line_num = fields.Char(size=80)
    connected_line_name = fields.Char(size=80)
    state = fields.Char(size=2)
    state_desc = fields.Char(size=256, string=_('State'))
    exten = fields.Char(size=32)
    callerid_num = fields.Char(size=32, string='CallerID number')
    callerid_name = fields.Char(size=32, string='CallerID name')
    system_name = fields.Char(size=128)
    accountcode = fields.Char(size=80)
    priority = fields.Char(size=4)
    app = fields.Char(size=32, string='Application')
    app_data = fields.Char(size=512, string='Application Data')
    language = fields.Char(size=2)
    cause = fields.Char(index=True)
    cause_txt = fields.Char(index=True)

    @api.model
    def create_from_event(self, channel, event):
        data = {
            'channel_id': channel.id,
            'event': event['Event'],
            'channel': event['Channel'],
            'state': event['ChannelState'],
            'state_desc': event['ChannelStateDesc'],
            'callerid_num': event['CallerIDNum'],
            'callerid_name': event['CallerIDName'],
            'connected_line_num': event['ConnectedLineNum'],
            'connected_line_name': event['ConnectedLineName'],
            'language': event['Language'],
            'accountcode': event['AccountCode'],
            'context': event['Context'],
            'exten': event['Exten'],
            'priority': event['Priority'],
            'uniqueid': event['Uniqueid'],
            'linkedid': event['Linkedid'],
            'cause': event.get('Cause'),
            'cause_txt': event.get('Cause-txt'),
        }
        self.create(data)

