import logging
from odoo import models, fields, api, tools, release, _
from odoo.exceptions import ValidationError, UserError
from .server import get_default_server
from .settings import debug

logger = logging.getLogger(__name__)


class PbxUser(models.Model):
    _name = 'asterisk_plus.user'
    _description = _('Asterisk User')

    exten = fields.Char()
    user = fields.Many2one('res.users', required=True,
                           ondelete='cascade',
                           # Exclude shared users
                           domain=[('share', '=', False)])
    name = fields.Char(related='user.name', readonly=True)
    #: Server where the channel is defined.
    server = fields.Many2one('asterisk_plus.server', required=True,
                             ondelete='restrict', default=get_default_server)
    channels = fields.One2many('asterisk_plus.user_channel',
                               inverse_name='asterisk_user')
    originate_vars = fields.Text(string='Channel Variables')
    open_partner_form = fields.Boolean(
        default=True,
        help=_('Open partner form on incoming calls from partner'))

    _sql_constraints = [
        ('exten_uniq', 'unique (exten,server)',
         _('This phone extension is already used!')),
        ('user_uniq', 'unique ("user",server)',
         _('This user is already defined!')),
    ]

    @api.model
    def create(self, vals):
        user = super(PbxUser, self).create(vals)
        if user and not self.env.context.get('no_clear_cache'):
            self.pool.clear_caches()
        return user

    def write(self, vals):
        user = super(PbxUser, self).write(vals)
        if user and not self.env.context.get('no_clear_cache'):
            self.pool.clear_caches()
        return user

    @api.model
    def has_asterisk_plus_group(self):
        """Used from notification.js to check if Odoo user is enabled to
        use Asterisk applications in order to start a bus listener.
        """
        if (self.env.user.has_group('asterisk_plus.group_asterisk_admin') or
                self.env.user.has_group(
                    'asterisk_plus.group_asterisk_user')):
            return True

    def _get_originate_vars(self):
        self.ensure_one()
        try:
            if not self.originate_vars:
                return []
            return [k for k in self.originate_vars.split('\n') if k]
        except Exception:
            logger.exception('Get originate vars error:')
            return []

    def dial_user(self):
        self.ensure_one()
        self.env.user.asterisk_users[0].server.originate_call(
            self.exten, model='asterisk_plus.user', res_id=self.id)

    def open_user_form(self):
        if self.env.user.has_group('asterisk_plus.group_asterisk_admin'):
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'asterisk_plus.user',
                'name': 'Users',
                'view_mode': 'tree,form',
                'view_type': 'form',
                'target': 'current',
            }
        else:
            if not self.env.user.asterisk_users:
                raise ValidationError('PBX user is not configured!')
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'asterisk_plus.user',
                'res_id': self.env.user.asterisk_users.id,
                'name': 'User',
                'view_id': self.env.ref(
                    'asterisk_plus.asterisk_plus_user_user_form').id,
                'view_mode': 'form',
                'view_type': 'form',
                'target': 'current',
            }

    @api.model
    @tools.ormcache('exten', 'system_name')
    def get_res_user_id_by_exten(self, exten, system_name):
        # TODO: Is it required?
        astuser = self.search([
            ('exten', '=', exten), ('system_name', '=', system_name)], limit=1)
        debug(self, 'GET RES USER BY EXTEN {} at {}: {}'.format(
            exten, system_name, astuser))
        return astuser.user.id
