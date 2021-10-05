# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2020
from datetime import datetime, timedelta
import json
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

logger = logging.getLogger(__name__)


class Channel(models.Model):
    _name = 'asterisk_plus.channel'
    _rec_name = 'channel'
    _description = 'Channel'

    #: Partner related to this channel.
    partner = fields.Many2one('res.partner', ondelete='set null')
    #: Odoo user who initiated the call related to this channel.
    owner = fields.Many2one(
        'asterisk_plus.user', string=_('Owner'),  ondelete='set null')
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

    ########################### COMPUTED FIELDS ###############################
    def _get_channel_short(self):
        # Makes SIP/1001-000000bd to be SIP/1001.
        for rec in self:
            rec.channel_short = '-'.join(rec.channel.split('-')[:-1])


    ########################### AMI Event handlers ############################

    @api.model
    def on_new_channel(self, event):
        """AMI NewChannel event is processed to create a new channel in Odoo.
        """
        pass

    @api.model
    def on_update_channel(self, event):
        """AMI UpdateChannel event is processed to create a new channel in Odoo.
        """
        pass

    @api.model
    def on_hangup(self, event):
        """Summary line.

        Extended description of function.

        Args:
            arg1 (int): Description of arg1
            arg2 (str): Description of arg2

        Returns:
            bool: Description of return value
            pass
        """
        pass

    @api.model
    def vacuum(self):
        self.search([]).unlink()
