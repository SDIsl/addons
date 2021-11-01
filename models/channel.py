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

    #: Partner related to this channel.
    partner = fields.Many2one('res.partner', ondelete='set null')
    #: Server of the channel. When server is removed all channels are deleted.
    server = fields.Many2one('asterisk_plus.server', ondelete='cascade')
    #: Channel name. E.g. SIP/1001-000000bd.
    channel = fields.Char(index=True)
    #: Channel unique ID. E.g. asterisk-1631528870.0
    uniqueid = fields.Char(size=150, index=True)
    #: Linked channel unique ID. E.g. asterisk-1631528870.1
    linkedid = fields.Char(size=150, index=True)
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
    callerid_num = fields.Char(size=32)
    #: Caller ID name.
    callerid_name = fields.Char(size=32)
    #: System name.
    system_name = fields.Char(size=32)
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

    #: Channel's short name. E.g. SIP/101
    channel_short = fields.Char(compute='_get_channel_short',
                                string=_('Channel'))
    # Hangup event fields
    active = fields.Boolean(default=True, index=True)
    cause = fields.Char(index=True)
    cause_txt = fields.Char(index=True)
    end_time = fields.Datetime(index=True)
    # Related object
    model = fields.Char()
    res_id = fields.Integer()

    ########################### COMPUTED FIELDS ###############################
    def _get_channel_short(self):
        # Makes SIP/1001-000000bd to be SIP/1001.
        for rec in self:
            rec.channel_short = '-'.join(rec.channel.split('-')[:-1])


    ########################### AMI Event handlers ############################

    @api.model
    def on_ami_new_channel(self, event):
        """AMI NewChannel event is processed to create a new channel in Odoo.
        """
        debug(self, 'NewChannel', event)
        # Find partner
        partner = self.env['res.partner'].sudo().search_by_number(event['CallerIDNum'])
        vals = {
            'partner': partner.id if partner else None,
            'channel': event['Channel'],
            'callerid_num': event['CallerIDNum'],
            'callerid_name': event['CallerIDName'],
            'connected_line_num': event['ConnectedLineNum'],
            'connected_line_name': event['ConnectedLineName'],
            'context': event['Context'],
            'exten': event['Exten'],
            'uniqueid': event['Uniqueid'],
            'linkedid': event['Linkedid'],
        }
        channel = self.env['asterisk_plus.channel'].search([('uniqueid', '=', event['Uniqueid'])])
        if not channel:
            channel = self.create(vals)
        else:
            channel.write(vals)
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
        uniqueid = event.get('Uniqueid')
        channel = event.get('Channel')
        found = self.env['asterisk_plus.channel'].search([('uniqueid', '=', uniqueid)])
        if not found:
            debug(self, 'Hangup', 'Channel {} not found for hangup.'.format(uniqueid))
            return False
        debug(self, 'Hangup', 'Found {} channel(s) {}'.format(len(found), channel))
        found.write({
            'active': False,
            'end_time': fields.Datetime.now(),
            'cause': event['Cause'],
            'cause_txt': event['Cause-txt'],
        })
        return found.id

    @api.model
    def ami_originate_response_failure(self, event):
        # This comes from Asterisk OriginateResponse AMI message when
        # call originate has been failed.
        if event['Response'] != 'Failure':
            logger.error(self, 'Response', 'UNEXPECTED ORIGINATE RESPONSE FROM ASTERISK!')
            return False
        channel = self.env['asterisk_plus.channel'].search([('uniqueid', '=', event['Uniqueid'])])
        if not channel:
            debug(self, 'Response', 'CHANNEL NOT FOUND FOR ORIGINATE RESPONSE!')
            return False
        if channel.cause:
            # This is a response after Hangup so no need for it.
            return channel.id
        channel.write({
            'active': False,
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
