# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2021
from datetime import datetime, timedelta
import json
import logging
import phonenumbers
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
    calling_number = fields.Char(index=True, readonly=True)
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
                           selection=[],
                            compute='_get_ref', inverse='_set_ref')
    notes = fields.Text()
    duration = fields.Integer(readonly=True, compute='_get_duration', store=True)
    duration_human = fields.Char(
        string=_('Call Duration'),
        compute='_get_duration_human')

    @api.model
    def create(self, vals):
        # Reload after call is created
        call = super(Call, self).create(vals)
        try:
            if not call.ref:
                call.update_reference()
        except Exception:
            logger.exception('Update call reference error:')
        finally:
            self.reload_calls()
            return call

    def update_reference(self):
        # Inherit in modules.
        pass

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
    def _get_ref(self):
        # We need a reference field to be computed because we want to
        # search and group by model.
        for rec in self:
            if rec.model and rec.model in self.env:
                try:
                    rec.ref = '%s,%s' % (rec.model, rec.res_id or 0)
                except ValueError as e:
                    logger.warning(e)
            else:
                rec.ref = None

    def _set_ref(self):
        for rec in self:
            if rec.ref:
                rec.write({'model': rec.ref._name, 'res_id': rec.ref.id})
            else:
                rec.write({'model': False, 'res_id': False})

    def _get_calling_name(self):
        """Returns the following according to the priority:
           1. Partner name.
           2. ref.name if reference is set and has name field.
           3. calling user name is reference is not set.
        """
        for rec in self:
            if rec.partner:
                rec.calling_name = rec.partner.name
            elif rec.ref and hasattr(rec.ref, 'name'):
                rec.calling_name = rec.ref.name
            elif rec.calling_user:
                rec.calling_name = rec.calling_user.name
            else:
                rec.calling_name = ''

    def _get_direction_icon(self):
        for rec in self:
            rec.direction_icon = '<span class="fa fa-arrow-left"/>' if rec.direction == 'in' else \
                '<span class="fa fa-arrow-right"/>'

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

    def add_note(self):
        return {
            'name': _("Add Notes"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'asterisk_plus.add_note_wizard',
            'target': 'new',
            'context': {'default_notes': self.notes}
        }

    @api.model
    def delete_calls(self):
        # Delete calls history
        days = self.env[
            'asterisk_plus.settings'].get_param('calls_keep_days')
        expire_date = datetime.utcnow() - timedelta(days=int(days))
        expired_calls = self.env['asterisk_plus.call'].search([
            ('ended', '<=', expire_date.strftime('%Y-%m-%d %H:%M:%S'))
        ])
        logger.info('Expired {} calls'.format(len(expired_calls)))
        expired_calls.unlink()

    @api.depends('answered', 'ended')
    def _get_duration(self):
        for rec in self:
            if rec.answered and rec.ended:
                rec.duration = (rec.ended - rec.answered).total_seconds()

    def _get_duration_human(self):
        for rec in self:
            rec.duration_human = str(timedelta(seconds=rec.duration))
