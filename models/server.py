# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2020
# -*- coding: utf-8 -*-
import base64
from datetime import datetime
import json
import logging
import time
import urllib
import uuid
from odoo import api, models, fields, SUPERUSER_ID, registry, release, _
from odoo.exceptions import ValidationError
try:
    import humanize
    HUMANIZE = False
except ImportError:
    HUMANIZE = False
import pepper
from .settings import debug

logger = logging.getLogger(__name__)


#: Click-to-call originate number format.
ORIGINATE_FORMAT_TYPES = [
    ('e164', _('E.164 Format')),
    ('out_of_country', _('Out of Country Format')),
    ('no_format', _('No Formatting')),
]


def get_default_server(rec):
    return rec.env.ref('asterisk_plus.default_server')


class Server(models.Model):
    _name = 'asterisk_plus.server'
    _description = "Asterisk Server"

    #: Server's name for humans.
    name = fields.Char(required=True)
    #: Server's minion ID.
    server_id = fields.Char(required=True, string='Server ID')

    def open_server_form(self):
        rec = self.env.ref('asterisk_plus.default_server')
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'asterisk_plus.server',
            'res_id': rec.id,
            'name': 'Agent',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
        }

    @api.model
    def _get_saltapi(self, force_login=False):
        """Get Salt API pepper instance.
        TODO: Cache auth in ORM cache not ir.config_parameter.
        Returns:
            A connected pepper instance. See `libpepper.py <https://github.com/saltstack/pepper/blob/develop/pepper/libpepper.py>`__ for details.
        """
        get_param = self.env['asterisk_plus.settings'].get_param
        saltapi = pepper.Pepper(get_param('saltapi_url'))
        # Get saltapi auth params
        auth = self.env[
            'ir.config_parameter'].sudo().get_param('saltapi_auth')
        # Check if we already logged in.
        if not force_login and auth:
            # Convert into dictionary.
            try:
                auth = json.loads(auth)
            except json.decoder.JSONDecodeError:
                auth = {'expire': 0}
            if auth['expire'] - time.time() < 0:
                # Token is no longer valid so need to login.
                logger.info('SALT API LOGIN AS TOKEN IS EXPIRED.')
                saltapi.login(
                    get_param('saltapi_user'),
                    get_param('saltapi_passwd'),
                    'file',
                )
                # Update auth data.
                self.env['ir.config_parameter'].set_param(
                    'saltapi_auth', json.dumps(saltapi.auth))
            else:
                # Token not expired, take it.
                saltapi.auth = auth
        else:
            # Token is no longer valid so need to login.
            logger.info('SALT API LOGIN.')
            saltapi.login(
                get_param('saltapi_user'),
                get_param('saltapi_passwd'),
                'file',
            )
            self.env['ir.config_parameter'].set_param(
                'saltapi_auth', json.dumps(saltapi.auth))
        return saltapi

    def salt_job(self, fun, arg=None, kwarg=None, timeout=None,
                  res_model=None, res_method=None, res_notify_uid=None,
                  pass_back=None, sync=False):
        """Execute a function on Salt minion.

        Args:
            fun (str): function name. Example: test.ping.
            arg (list): positional arguments.
            kwarg (dict): named arguments.
            timeout (int): function execution timeout in seconds.
            res_model (str): name of the model to receive function result.
            res_method (str): name of the method to receive function result. Function result is passed as the 1-st paramater.
            res_notify_uid (int): User ID that will receive function result in notification message.
            pass_back (dict): json serializable dictionary that is passed to res_method as the 2-nd paramater.
        """
        try:
            saltapi = self.sudo()._get_saltapi()
        except urllib.error.URLError:
            raise ValidationError('Cannot connect to Salt API process.')
        # Wrap calling function to be able to re-login on session expiration.

        def call_fun():
            if not sync:
                ret = saltapi.local_async(tgt=self.server_id, fun=fun, arg=arg,
                                          kwarg=kwarg, timeout=timeout, ret='odoo')
            else:
                ret = saltapi.local(tgt=self.server_id, fun=fun, arg=arg,
                                    kwarg=kwarg, timeout=timeout)
            # TODO: Add server:
            # {'return': [{'jid': '20210928122846179815', 'minions': ['asterisk']}]}
            debug(self, 'Return', ret)
            if not sync:
                # Create a Salt job.
                self.env['asterisk_plus.salt_job'].sudo().create({
                    'jid': ret['return'][0]['jid'],
                    'res_model': res_model,
                    'res_method': res_method,
                    'res_notify_uid': res_notify_uid,
                    'pass_back': json.dumps(pass_back) if pass_back else False,
                })
            if not self.env.context.get('no_commit'):
                # Commit ASAP so that returner can find the job.
                self.env.cr.commit()
            return ret
        try:
            return call_fun()
        except KeyError as e:
            if 'jid' in str(e):
                raise ValidationError('No job ID was returned. Check Salt connectivity.')
        except pepper.exceptions.PepperException as e:
            if 'Authentication denied' in str(e):
                saltapi = self.sudo()._get_saltapi(force_login=True)
                return call_fun()
            else:
                raise

    def ami_action(self, action, timeout=5, no_wait=False, as_list=None, **kwargs):
        """Send AMI action to the server.

        Args:
            action (dict): A dictionary with action.

        Returns:
            A list of results as received from Asterisk.

        Example action:

        .. code:: python

            {'Action': 'Ping'}

        Result:

        .. code:: python

            [{'Response': 'Success', 'ActionID': 'action/67cfd99b-8138-4cb5-9473-4e8be6d1cbe9/1/5026', 'Ping': 'Pong', 'Timestamp': '1631707333.341870', 'content': ''}]        

        """
        return self.salt_job(
            fun='asterisk.manager_action',
            arg=action,
            kwarg={
                'timeout': timeout,
                'no_wait': no_wait,
                'as_list': as_list
            }, **kwargs)

    ##################### UI BUTTONS ==========================================

    def ping(self):
        """Called from server form to test the connectivity.

        Returns:
            True or False if Salt minion is not connected.
        """
        return self.salt_job(fun='test.ping',
                             res_model='asterisk_plus.server',
                             res_method='ping_reply',
                             pass_back={'uid': self.env.user.id})

    @api.model
    def ping_reply(self, data, pass_back):
        self.env.user.asterisk_plus_notify(str(data), uid=pass_back['uid'])


    def asterisk_ping(self):
        """Called from server form to test AMI connectivity.
        """
        res = self.ami_action({'Action': 'Ping'})
        # res_notify_uid=self.env.uid,
        #    res_model='asterisk_plus.server', res_method='asterisk_ping_again')
        debug(self, 'Sync rec', res)
        return res
        # self.env.user.asterisk_plus_notify(str(res))
        return res

    @api.model
    def asterisk_ping_again(self, data, pass_back):
        debug(self, 'Ping again', None)
        self.env.ref('asterisk_plus.default_server').sudo().asterisk_ping()

    @api.model
    def on_fully_booted(self, event):
        return True

    @api.model
    def originate_call(self, number, model=None, res_id=None, user=None):
        if not user:
            user = self.env.user
        if not user.asterisk_users:
            raise ValidationError('PBX User is not defined!') # sdd sd sd sd sdsd sdsd s
        asterisk_user = self.env.user.asterisk_users[0]
        variables = asterisk_user._get_originate_vars()
        if not asterisk_user.channels:
            raise ValidationError('SIP channels not defined for user!')
        originate_channels = [k for k in asterisk_user.channels if k.originate_enabled]
        if not originate_channels:
            raise ValidationError('No channels with originate enabled!')
        for ch in originate_channels:            
            channel_vars = variables.copy()
            if ch.auto_answer_header:
                header = ch.auto_answer_header
                try:
                    pos = header.find(':')
                    param = header[:pos]
                    val = header[pos+1:]
                    if 'PJSIP' in ch.name.upper():
                        ch.append(
                            'PJSIP_HEADER(add,{})={}'.format(
                                param.lstrip(), val.lstrip()))
                    else:
                        channel_vars.append(
                            'SIPADDHEADER={}: {}'.format(
                                param.lstrip(), val.lstrip()))
                except Exception:
                    logger.warning(
                        'Cannot parse auto answer header: %s', header)

            channel_id = uuid.uuid4().hex
            other_channel_id = uuid.uuid4().hex
            self.env['asterisk_plus.channel'].create({
                    'channel': ch.name,
                    'uniqueid': channel_id,
                    'linkedid': other_channel_id,
                    # TODO: Think about multi server.
                    'owner': self.env.user.asterisk_users[0].id
            })
            if not self.env.context.get('no_commit'):
                self.env.cr.commit()
            action = {
                'Action': 'Originate',
                'Context': ch.originate_context,
                'Priority': '1',
                'Timeout': 60000,
                'Channel': ch.name,
                'Exten': number,
                'Async': 'true',
                'EarlyMedia': 'true',
                # 'CallerID': callerid,
                'ChannelId': channel_id,
                'OtherChannelId': other_channel_id,
                'Variable': channel_vars,
            },

            ch.server.ami_action(action, res_model='asterisk_plus.server',
                                 res_method='originate_call_response',
                                 pass_back={'uid': self.env.user.id})

    @api.model
    def originate_call_response(self, data, pass_back):
        debug(self, 'Originate', data)
        if data[0]['Response'] == 'Error':
            self.env.user.asterisk_plus_notify(
                data[0]['Message'], uid=pass_back['uid'], warning=True)

    @api.model
    def ami_originate_response(self, data):
        # This comes from Asterisk OriginateResponse AMI message when
        # call originate has been failed.
        logger.info(data)
        reason = data.get('Reason')
        uniqueid = data.get('Uniqueid')
        channel = self.env['asterisk_plus.channel'].sudo().search([('uniqueid', '=', uniqueid)])
        if channel:
            self.env.user.asterisk_plus_notify(
                _('Call failed, reason {0}').format(reason),
                uid=channel.create_uid.id, warning=True)
        return True
