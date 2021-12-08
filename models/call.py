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
    calling_name = fields.Char(compute='_get_calling_name')
    called_number = fields.Char(index=True)
    started = fields.Datetime(index=True)
    answered = fields.Datetime(index=True)
    ended = fields.Datetime(index=True)
    direction = fields.Selection(selection=[('in', 'Incoming'), ('out', 'Outgoing')],
        index=True)
    direction_icon = fields.Html(string='Dir', compute='_get_direction_icon')
    status = fields.Selection(selection=[
         ('noanswer', 'No Answer'), ('answered', 'Answered'),
         ('busy', 'Busy'), ('failed', 'Failed'),
         ('progress', 'In Progress')], index=True, default='progress')
    # Boolean index for split all calls on this flag. Calls are by default in active state.
    is_active = fields.Boolean(index=True, default=True)
    channels = fields.One2many('asterisk_plus.channel', inverse_name='call')
    partner = fields.Many2one('res.partner', ondelete='set null')
    calling_user = fields.Many2one('res.users', ondelete='set null')
    called_user = fields.Many2one('res.users', ondelete='set null')
    # Related object
    model = fields.Char()
    res_id = fields.Integer()
    ref = fields.Reference(string='Reference',
                           selection=[('res.partner', _('Partners')),
                                      ('asterisk_plus.user', _('Users'))],
                           compute='_compute_ref',
                           readonly=True)

    @api.model
    def create(self, vals):
        # Reload after call is created
        self.reload_calls()
        return super(Call, self).create(vals)

    @api.constrains('is_active')
    def reload_on_hangup(self):
        for rec in self:
            if not rec.is_active:
                self.reload_calls()

    @api.constrains('called_user')
    def notify_called_user(self):
        for rec in self:
            if rec.called_user:
                message = 'Incoming call from {}'.format(rec.calling_name)
                self.env['res.users'].asterisk_plus_notify(
                    message, uid=rec.called_user.id)

    @api.depends('model', 'res_id') 
    def _compute_ref(self):
        for rec in self:
            if rec.model and rec.model in self.env:
                rec.ref = '%s,%s' % (rec.model, rec.res_id or 0)
            else:
                rec.ref = None

    def _get_calling_name(self):
        """Returns the following according to the priority:
           1. ref.name if reference is set and has name field.
           2. calling user name is reference is not set.
        """
        for rec in self:
            if rec.ref and hasattr(rec, 'name'):
                rec.calling_name = rec.ref.name
            elif rec.calling_user:
                rec.calling_name = rec.calling_user.name
            else:
                rec.calling_name = ''

    def _get_direction_icon(self):
        for rec in self:
            rec.direction_icon = '<span class="fa fa-arrow-left"/>' if rec.direction == 'in' else \
                '<span class="fa fa-arrow-right"/>'

    def _get_call_users(self):
        for rec in self:
            user_channel = self.env['asterisk_plus.user_channel'].get_user_channel(
                rec.channel, rec.system_name)
            if user_channel:
                if user_channel.originate_context == rec.context:
                    debug(self, 'Src user: {}'.format(user_channel.sudo().asterisk_user.user.name))
                    rec.calling_user = user_channel.sudo().asterisk_user.user.id
                    if rec.parent_channel.called_user:
                        rec.called_user = rec.parent_channel.called_user
                    else:
                        rec.called_user = False
                else:
                    debug(self, 'Dst user: {}'.format(user_channel.sudo().asterisk_user.user.name))
                    rec.called_user = user_channel.sudo().asterisk_user.user.id
                    if rec.parent_channel.calling_user:
                        rec.calling_user = rec.parent_channel.calling_user
                    else:
                        rec.calling_user = False
            else:
                rec.calling_user = False
                rec.called_user = False

    def reload_calls(self, data=None):
        if data is None:
            data = {}
        msg = {
            'action': 'reload_view',
            'model': 'asterisk_plus.call'
        }
        self.env['bus.bus'].sendone('asterisk_plus_actions', json.dumps(msg))

    def move_to_history(self):
        self.is_active = False
