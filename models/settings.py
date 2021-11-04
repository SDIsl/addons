# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2020
import inspect
import logging
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from odoo.tools import ormcache

logger = logging.getLogger(__name__)

FORMAT_TYPE = 'e164'


def debug(rec, prefix, message=None):
    caller_module = inspect.stack()[1][3]
    if rec.env['asterisk_plus.settings'].sudo().get_param('debug_mode'):
        print('++++++ {}: {}: {}'.format(
            caller_module, prefix.upper(), message))


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
    permit_ip_addresses = fields.Char(
        string=_('Permit IP address(es)'),
        help=_('Comma separated list of IP addresses permitted to query caller'
               ' ID number, etc. Leave empty to allow all addresses.'))
    originate_context = fields.Char(
        string='Default context',
        default='from-internal', required=True,
        help='Default context to set when creating PBX / Odoo user mapping.')
    originate_timeout = fields.Integer(default=60, required=True)

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
            debug(self, 'set_param', "Keeping existing value for param: {}".format(param))
        return True

    @api.model
    def create(self, vals):
        self.clear_caches()
        return super(Settings, self).create(vals)

    def write(self, vals):
        self.clear_caches()
        return super(Settings, self).write(vals)
