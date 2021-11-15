# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2020
from datetime import datetime, timedelta
import json
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from .server import debug

logger = logging.getLogger(__name__)


class Channel(models.Model):
    _name = 'asterisk_plus.channel'
    _rec_name = 'channel'
    _order = 'id desc'
    _description = 'Channel'

    #: Call of the channel
    call = fields.Many2one('asterisk_plus.call', ondelete='cascade')
    #: Server of the channel. When server is removed all channels are deleted.
    server = fields.Many2one('asterisk_plus.server', ondelete='cascade')
    #: Channel name. E.g. SIP/1001-000000bd.
    channel = fields.Char(index=True)
    #: Shorted channel to compare with user's channel as it is defined. E.g. SIP/1001
    channel_short = fields.Char(compute='_get_channel_short',
                                string=_('Channel'))
    #: Channels that were created from this channel.
    linked_channels = fields.One2many('asterisk_plus.channel',
        inverse_name='parent_channel')
    #: Parent channel
    parent_channel = fields.Many2one('asterisk_plus.channel', compute='_get_parent_channel')
    #: Channel unique ID. E.g. asterisk-1631528870.0
    uniqueid = fields.Char(size=64, index=True)
    #: Linked channel unique ID. E.g. asterisk-1631528870.1
    linkedid = fields.Char(size=64, index=True, string='Linked ID')
    #: Channel context.
    context = fields.Char(size=80)
    # Connected line number.
    connected_line_num = fields.Char(size=80)
    #: Connected line name.
    connected_line_name = fields.Char(size=80)
    #: Channel's current state.
    state = fields.Char(size=80)
    #: Channel's current state description.
    state_desc = fields.Char(size=256, string=_('State'))
    #: Channel extension.
    exten = fields.Char(size=32)
    #: Caller ID number.
    callerid_num = fields.Char(size=32, string='CallerID number')
    #: Caller ID name.
    callerid_name = fields.Char(size=32, string='CallerID name')
    #: System name.
    system_name = fields.Char(size=128)
    #: Channel's account code.
    accountcode = fields.Char(size=80)
    #: Channel's current priority.
    priority = fields.Char(size=4)
    #: Channel's current application.
    app = fields.Char(size=32, string='Application')
    #: Channel's current application data.
    app_data = fields.Char(size=512, string='Application Data')
    #: Channel's language.
    language = fields.Char(size=2)
    # Hangup event fields
    cause = fields.Char(index=True)
    cause_txt = fields.Char(index=True)
    hangup_date = fields.Datetime(index=True)
    # Related object
    model = fields.Char()
    res_id = fields.Integer()
    timestamp = fields.Char(size=20)
    event = fields.Char(size=64)

    obj = fields.Reference(string='Reference',
                           selection=[('res.partner', _('Partners')),
                                      ('asterisk_plus.user', _('Users'))],
                           compute='_compute_obj',
                           readonly=True)

    @api.depends('model', 'res_id') 
    def _compute_obj(self):
        for rec in self:
            if rec.model and rec.model in self.env:
                rec.obj = '%s,%s' % (rec.model, rec.res_id or 0)
            else:
                rec.obj = None

    ########################### COMPUTED FIELDS ###############################
    def _get_channel_short(self):
        # Makes SIP/1001-000000bd to be SIP/1001.
        for rec in self:
            rec.channel_short = '-'.join(rec.channel.split('-')[:-1])

    def _get_parent_channel(self):
        for rec in self:
            if rec.uniqueid != rec.linkedid:
                # Asterisk bound channels
                rec.parent_channel = self.search(
                    [('uniqueid', '=', rec.linkedid)], limit=1)
            else:
                rec.parent_channel = False

    def _get_linked_channels(self):
        for rec in self:
            print(rec)
            print(self.search(
                [('linkedid', '=', rec.uniqueid)]))
            rec.linked_channels = self.search(
                [('linkedid', '=', rec.uniqueid), ('id', '!=', rec.id)])

    def reload_channels(self, data={}):
        self.ensure_one()
        msg = {
            'event': 'update_channel',
            'dst': self.exten,
            'system_name': self.system_name,
            'channel': self.channel_short,
            'auto_reload': True
        }
        self.env['bus.bus'].sendone('asterisk_plus_channels', json.dumps(msg))

    def update_call_data(self):
        self.ensure_one()
        # First check the channel owner.
        user_channel = self.env['asterisk_plus.user_channel'].get_user_channel(
            self.channel, self.system_name)
        debug(self, 'User channel: {}'.format(user_channel.name))
        if user_channel:
            if len(self.call.channels) == 1: # This is the primary channel.
                # We use sudo() as server does not have access to res.users.
                self.call.write({
                    'calling_user': user_channel.sudo().asterisk_user.user.id,
                    'partner': self.env['res.partner'].search_by_number(self.exten)
                })
            else: # Secondady channel that means user is called
                self.call.called_user = user_channel.sudo().asterisk_user.user.id
        else: # No user channel is found. Try to match the partner.
            # No user channel try to match the partner by caller ID number
            self.call.partner = self.env['res.partner'].search_by_number(self.callerid_num)

    ########################### AMI Event handlers ############################
    @api.model
    def update_channel_state(self, event):
        debug(self, json.dumps(event, indent=2))
        get = event.get
        data = {
            'server': self.env.user.asterisk_server.id,
            'channel': get('Channel'),
            'uniqueid': get('Uniqueid'),
            'linkedid': get('Linkedid'),
            'context': get('Context'),
            'connected_line_num': get('ConnectedLineNum'),
            'connected_line_name': get('ConnectedLineName'),
            'state': get('ChannelState'),
            'state_desc': get('ChannelStateDesc'),
            'exten': get('Exten'),
            'callerid_num': get('CallerIDNum'),
            'callerid_name': get('CallerIDName'),
            'accountcode': get('AccountCode'),
            'priority': get('Priority'),
            'timestamp': get('Timestamp'),
            'system_name': get('SystemName', 'asterisk'),
            'language': get('Language'),
            'event': get('Event'),
        }
        channel = self.env['asterisk_plus.channel'].search([('uniqueid', '=', get('Uniqueid'))], limit=1)
        if not channel:
            channel = self.create(data)
        else:
            channel.write(data)
        if self.env['asterisk_plus.settings'].sudo().get_param('trace_ami'):
            data['channel_id'] = channel.id
            self.env['asterisk_plus.channel_message'].create_from_event(channel, event)
        return channel

    @api.model
    def on_ami_new_channel(self, event):
        """AMI NewChannel event is processed to create a new channel in Odoo.
        """
        debug(self, json.dumps(event, indent=2))
        # Create a call for the primary channel.
        if event['Uniqueid'] == event['Linkedid']:
            call = self.env['asterisk_plus.call'].create({
                'uniqueid': event['Uniqueid'],
                'calling_number': event['CallerIDNum'],
                'called_number': event['Exten'],
                'started': datetime.now(),
                'is_active': True,
                'status': 'progress',
            })
        else:
            # There is already a parent channel and the call
            call = self.env['asterisk_plus.call'].search(
                [('uniqueid', '=', event['Linkedid'])], limit=1)
        data = {
            'call': call.id,
            'event': event['Event'],
            'server': self.env.user.asterisk_server.id,
            'channel': event['Channel'],
            'state': event['ChannelState'],
            'state_desc': event['ChannelStateDesc'],
            'callerid_num': event['CallerIDNum'],
            'callerid_name': event['CallerIDName'],
            'connected_line_num': event['ConnectedLineNum'],
            'connected_line_name': event['ConnectedLineName'],
            'language': event['Language'],
            'accountcode': event['AccountCode'],
            'priority': event['Priority'],
            'context': event['Context'],
            'exten': event['Exten'],
            'uniqueid': event['Uniqueid'],
            'linkedid': event['Linkedid'],
            'system_name': event['SystemName'],
        }
        channel = self.env['asterisk_plus.channel'].search([('uniqueid', '=', event['Uniqueid'])])
        if not channel:
            channel = self.create(data)
        else:
            channel.write(data)
        # Update call based on channel.
        channel.update_call_data()
        channel.reload_channels()
        if self.env['asterisk_plus.settings'].sudo().get_param('trace_ami'):
            data['channel_id'] = channel.id
            self.env['asterisk_plus.channel_message'].create_from_event(channel, event)
        return channel.id

    @api.model
    def on_ami_hangup(self, event):
        """Summary line.

        Extended description of function.

        Args:
            arg1 (int): Description of arg1
            arg2 (str): Description of arg2

        Returns:
            bool: Description of return value
            pass
        """
        debug(self, json.dumps(event, indent=2))            
        # TODO: Limit search domain by create_date less then one day.
        channel = self.env['asterisk_plus.channel'].search([('uniqueid', '=', event['Uniqueid'])])
        if not channel:
            debug(self, 'Channel {} not found for hangup.'.format(event['Channel']))
            return False
        debug(self, 'Found {} channel(s) {}'.format(len(channel), event['Channel']))
        data = {
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
            'hangup_date': fields.Datetime.now(),
            'cause': event['Cause'],
            'cause_txt': event['Cause-txt'],
        }
        channel.write(data)
        # Set call status by the originated channel
        if event['Uniqueid'] == event['Linkedid']:
            channel.call.write({
                'status': 'answered',
                'is_active': False,
                'ended': datetime.now(),
            })
        channel.reload_channels({'event': 'hangup_channel'})
        if self.env['asterisk_plus.settings'].sudo().get_param('trace_ami'):
            # Remove and add fields according to the message
            data['channel_id'] = channel.id
            self.env['asterisk_plus.channel_message'].create_from_event(channel, event)
        return channel.id

    @api.model
    def ami_originate_response_failure(self, event):
        # This comes from Asterisk OriginateResponse AMI message when
        # call originate has been failed.
        if event['Response'] != 'Failure':
            logger.error(self, 'Response', 'UNEXPECTED ORIGINATE RESPONSE FROM ASTERISK!')
            return False
        channel = self.env['asterisk_plus.channel'].search([('uniqueid', '=', event['Uniqueid'])])
        if not channel:
            debug(self, 'CHANNEL NOT FOUND FOR ORIGINATE RESPONSE!')
            return False
        if channel.cause:
            # This is a response after Hangup so no need for it.
            return channel.id
        channel.write({
            'cause': event['Reason'],  # 0
            'cause_txt': event['Response'],  # Failure
        })
        reason = event.get('Reason')
        if channel and channel.model and channel.res_id:
            self.env.user.asterisk_plus_notify(
                _('Call failed, reason {0}').format(reason),
                uid=channel.create_uid.id, warning=True)
        return channel.id

    @api.model
    def vacuum(self):
        self.search([]).unlink()
