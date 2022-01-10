from datetime import datetime, timedelta
import json
import logging
import pytz
import uuid
from odoo import models, fields, api
from odoo.addons.asterisk_plus.models.server import get_default_server
from odoo.addons.asterisk_plus.models.settings import debug

logger = logging.getLogger(__name__)


class Callback(models.Model):
    _name = 'asterisk_plus_callback.callback'
    _description = 'Callback Request'
    _order = 'id desc'
    _rec_name = 'id'

    # Wait for CallbackDone UserEvent to set status to Done.
    done_by_event = fields.Boolean(
        help='Wait for CallbackDone UserEvent to set status to Done.')
    # CallerID number
    clid_number = fields.Char(required=True)
    # Originate channel: PJSIP/{}@provider
    channel = fields.Char(required=True)
    # Originated channels
    channels = fields.One2many(
        'asterisk_plus.channel',
        inverse_name='callback',
        context={'active_test': False})
    # Origination context
    context = fields.Char(required=True)
    # Originated number
    exten = fields.Char(required=True)
    # Channel variables
    variables = fields.Text()
    # Delay before first call in minutes
    delay = fields.Integer(default=2)
    not_after_stored = fields.Char()
    not_after = fields.Char(
        compute='_get_not_after',
        inverse='_set_not_after',
        default=lambda self: self.env['asterisk_plus.settings'].get_param(
            'callback_not_after')
    )
    not_before_stored = fields.Char()
    not_before = fields.Char(
        compute='_get_not_before',
        inverse='_set_not_before',
        default=lambda self: self.env['asterisk_plus.settings'].get_param(
            'callback_not_before')
    )
    attempt_interval = fields.Integer(
        default=lambda self: self.env['asterisk_plus.settings'].get_param(
            'callback_attempt_interval')
    )
    daily_attempts = fields.Integer(
        default=lambda self: self.env['asterisk_plus.settings'].get_param(
            'callback_daily_attempts')
    )
    max_attempts = fields.Integer(
        default=lambda self: self.env['asterisk_plus.settings'].get_param(
            'callback_max_attempts')
    )
    # Count number of attempts done
    max_attempts_done = fields.Integer()
    # Count number daily attempts done
    daily_attempts_done = fields.Integer()
    status = fields.Selection(selection=[
        ('progress', 'In Progress'),
        ('done', 'Done'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    ], default='progress')

    @api.model
    def create(self, vals):
        res = super(Callback, self).create(vals)
        self.wakeup()
        return res

    def _get_not_after(self):
        for rec in self:
            # Convert to datetime
            not_after_stored = datetime.strptime(rec.not_after_stored, '%H:%M')
            # Need UTC time to get correct timezone offset
            now = datetime.now()
            # Get user timezone
            tz = pytz.timezone(self.env.user.tz)
            # Get timezone offset value
            offset = tz.utcoffset(now)
            # Adjust time with user timezone
            user_time = not_after_stored + offset
            # Convert to string and save
            rec.not_after = datetime.strftime(user_time, '%H:%M')

    def _set_not_after(self):
        for rec in self:
            # Convert to datetime
            not_after = datetime.strptime(rec.not_after, '%H:%M')
            # Need UTC time to get correct timezone offset
            now = datetime.now()
            # Get user timezone
            tz = pytz.timezone(self.env.user.tz)
            # Get timezone offset value
            offset = tz.utcoffset(now)
            # Convert to UTC time
            utc_time = not_after - offset
            # Convert to string and save
            rec.not_after_stored = datetime.strftime(utc_time, '%H:%M')

    def _get_not_before(self):
        for rec in self:
            # Convert to datetime
            not_before_stored = datetime.strptime(rec.not_before_stored, '%H:%M')
            # Need UTC time to get correct timezone offset
            now = datetime.now()
            # Get user timezone
            tz = pytz.timezone(self.env.user.tz)
            # Get timezone offset value
            offset = tz.utcoffset(now)
            # Adjust time with user timezone
            user_time = not_before_stored + offset
            # Convert to string and save
            rec.not_before = datetime.strftime(user_time, '%H:%M')

    def _set_not_before(self):
        for rec in self:
            # Convert to datetime
            not_before = datetime.strptime(rec.not_before, '%H:%M')
            # Need UTC time to get correct timezone offset
            now = datetime.now()
            # Get user timezone
            tz = pytz.timezone(self.env.user.tz)
            # Get timezone offset value
            offset = tz.utcoffset(now)
            # Convert to UTC time
            utc_time = not_before - offset
            # Convert to string and save
            rec.not_before_stored = datetime.strftime(utc_time, '%H:%M')

    def wakeup(self):
        callbacks = self.env['asterisk_plus_callback.callback'].search([
            ('status', '=', 'progress')])
        if not callbacks:
            debug(self, 'No callbacks in progress state found.')
            return False
        for callback in callbacks:
            now = datetime.now()
            delay = callback.create_date + timedelta(minutes=callback.delay)
            interval = callback.write_date + timedelta(minutes=callback.attempt_interval)
            next_day = callback.write_date + timedelta(days=1)
            # Callback time bounds
            current_time = datetime.strptime(now.strftime('%H:%M'), '%H:%M').time()
            not_before = datetime.strptime(callback.not_before_stored, '%H:%M').time()
            not_after = datetime.strptime(callback.not_after_stored, '%H:%M').time()

            """
            # Omit callback round if active call is in progress
            if callback.channels.filtered(lambda x: x.active is True):
                debug(self, 'Callback {} has active call. Omitting...'.format(callback.id))
                continue
            """
            # Check if callback is delayed
            if now < delay:
                debug(self, 'Callback {} delayed.'.format(callback.id))
                continue
            # Omit round if callback violates interval
            if now < interval:
                debug(self, 'Callback {} violates interval.'.format(callback.id))
                continue
            # Check if callback fits time frame
            if not (not_before < current_time < not_after):
                debug(self, 'Callback {} not in a time frame.'.format(callback.id))
                continue
            # If max_attempts reached set callback status to expired
            if callback.max_attempts == callback.max_attempts_done:
                debug(self, 'Callback {} max attempts reached.'.format(callback.id))
                callback.status = 'expired'
                continue
            # Reset daily_attempts_done counter on next day
            if next_day.day == now.day:
                debug(self, 'New day, reset daily_attempts_done counter.')
                callback.daily_attempts_done = 0
            # Don't callback if daily attempts reached
            if callback.daily_attempts == callback.daily_attempts_done:
                debug(self, 'Callback {} daily attempts reached.'.format(callback.id))
                continue

            # All requirements passed, originate
            callback.write({
                'max_attempts_done': callback.max_attempts_done + 1,
                'daily_attempts_done': callback.daily_attempts_done + 1,
            })
            self.originate_callback(callback)

    def originate_callback(self, callback):
        channel_id = uuid.uuid4().hex
        other_channel_id = uuid.uuid4().hex
        channel = self.env['asterisk_plus.channel'].create({
            'server': get_default_server(self).id,
            'uniqueid': channel_id,
            'linkedid': other_channel_id,
            'callback': callback.id,
            'channel': callback.channel,
        })
        action = {
            'Action': 'Originate',
            'Context': callback.context,
            'Priority': '1',
            'Timeout': 60000,
            'Channel': callback.channel,
            'Exten': callback.exten,
            'Async': 'true',
            'EarlyMedia': 'true',
            'ChannelId': channel_id,
            'OtherChannelId': other_channel_id,
        }
        if callback.clid_number:
            action.update({'CallerID': callback.clid_number})
        if callback.variables:
            action.update({'Variable': callback.variables.split('\n')})
        channel.server.ami_action(
            action,
            res_model='asterisk_plus.channel',
            res_method='callback_originate_call_response',
            pass_back={'channel_id': channel_id})

    @api.model
    def on_callback_done(self, event):
        debug(self, json.dumps(event, indent=2))
        channel = self.env['asterisk_plus.channel'].with_context(
            active_test=False).search([('uniqueid', '=', event['Uniqueid'])])
        if not channel:
            logger.error('Channel not found for callback: %s', event)
            return False
        if channel.callback:
            channel.callback.status = 'done'
            debug(self, 'Setting done status for channel {} callback'.format(
                channel.channel))
            return True
        elif channel.parent_channel.callback:
            channel.parent_channel.callback = 'done'
            debug(self, 'Setting done status for parent channel {} callback'.format(
                channel.channel))
            return True
        else:
            debug(self, 'Channel {} callback not found.'.format(channel.channel))
            return False
