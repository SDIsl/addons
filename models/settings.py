# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2020
import inspect
import logging
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from odoo.tools import ormcache

logger = logging.getLogger(__name__)

FORMAT_TYPE = 'e164'


def debug(rec, message):
    caller_module = inspect.stack()[1][3]
    if rec.env['asterisk_plus.settings'].sudo().get_param('debug_mode'):
        print('++++++ {}: {}'.format(caller_module, message))


class Settings(models.Model):
    """One record model to keep all settings. The record is created on 
    get_param / set_param methods on 1-st call.
    """
    _name = 'asterisk_plus.settings'
    _description = 'Settings'

    #: Just a friends name for a settings form.
    name = fields.Char(compute='_get_name')
    #: Salt API URL, e.g. https://localhost:8000/
    saltapi_url = fields.Char(required=True, default='https://127.0.0.1:8000',
                              string='Salt API URL')
    #: Salt API user.e.g. saltdev
    saltapi_user = fields.Char(required=True, string='Salt API User',
                               default='odoo')
    #: Salt API password .e.g. saltdev
    saltapi_passwd = fields.Char(required=True, string='Salt API Password',
                                 default='odoo')
    #: Debug mode
    debug_mode = fields.Boolean()
    #: Save all AMI messages on channels
    trace_ami = fields.Boolean(string='Trace AMI',
        help='Save all AMI messages on channels')
    permit_ip_addresses = fields.Char(
        string=_('Permit IP address(es)'),
        help=_('Comma separated list of IP addresses permitted to query caller'
               ' ID number, etc. Leave empty to allow all addresses.'))
    originate_context = fields.Char(
        string='Default context',
        default='from-internal', required=True,
        help='Default context to set when creating PBX / Odoo user mapping.')
    originate_timeout = fields.Integer(default=60, required=True)
    # Recording settings
    record_calls = fields.Boolean(
        default=True,
        help=_("If checked, call recording will be enabled"))
    delete_recordings = fields.Boolean(
        default=True,
        help='Keep recordings on Asterisk after upload to Odoo.')
    use_mp3_encoder = fields.Boolean(
        default=False, string=_("Encode to MP3"),
        help=_("If checked, call recordings will be encoded using MP3"
               "Requires lameenc Python package installed to work."))
    mp3_encoder_bitrate = fields.Selection(
        selection=[('16', '16kbps'),
                   ('32', '32kbps'),
                   ('48', '48kbps'),
                   ('64', '64kbps'),
                   ('96', '96kbps'),
                   ('128', '128 kbps')],
        required=False)
    mp3_encoder_quality = fields.Selection(
        selection=[('2', '2-Highest'),
                   ('3', '3'),
                   ('4', '4'),
                   ('5', '5'),
                   ('6', '6'),
                   ('7', '7-Fastest')],
        required=False)

    @api.model
    def _get_name(self):
        for rec in self:
            rec.name = 'General Settings'

    def open_settings_form(self):
        rec = self.env['asterisk_plus.settings'].search([])
        if not rec:
            rec = self.sudo().create({})
        else:
            rec = rec[0]
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'asterisk_plus.settings',
            'res_id': rec.id,
            'name': 'General Settings',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
        }

    @api.model
    @ormcache('param')
    def get_param(self, param, default=False):
        """
        """
        data = self.search([])
        if not data:
            data = self.sudo().create({})
        else:
            data = data[0]
        return getattr(data, param, default)

    @api.model
    def set_param(self, param, value, keep_existing=False):
        """
        """
        data = self.search([])
        if not data:
            data = self.sudo().create({})
        else:
            data = data[0]
        # Check if the param is already there.
        if not keep_existing or not getattr(data, param):
            # TODO: How to handle Boolean fields!?
            setattr(data, param, value)
        else:
            debug(self, "Keeping existing value for param: {}".format(param))
        return True

    @api.model
    def create(self, vals):
        self.clear_caches()
        return super(Settings, self).create(vals)

    def write(self, vals):
        self.clear_caches()
        return super(Settings, self).write(vals)

    @api.constrains('record_calls')
    def record_calls_toggle(self):
        # Enable/disable call recording event
        recording_event = self.env.ref('asterisk_plus.var_set_mixmon')
        # Check if enent can be updated
        if recording_event.update == 'no':
            raise ValidationError(
                _('Event {} is not updatebale'.format(recording_event.name)))
        recording_event.is_enabled = True if self.record_calls is True else False
        # Reload events map
        server = self.env.ref('asterisk_plus.default_server')
        server.ami_action(
            {'Action': 'ReloadEvents'},
        )

    @api.constrains('use_mp3_encoder')
    def _check_lameenc(self):
        try:
            import lameenc
        except ImportError:
            for rec in self:
                if rec.use_mp3_encoder:
                    raise ValidationError(
                        "Please install lameenc to enable MP3 encoding"
                        "(pip3 install lameenc).")

    @api.onchange('use_mp3_encoder')
    def on_change_mp3_encoder(self):
        for rec in self:
            if rec.use_mp3_encoder:
                rec.mp3_encoder_bitrate = '96'
                rec.mp3_encoder_quality = '4'
