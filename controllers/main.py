# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2020
import logging
from odoo import http, SUPERUSER_ID, registry
from odoo.api import Environment
from werkzeug.exceptions import BadRequest

logger = logging.getLogger(__name__)


class AsteriskPlusController(http.Controller):

    @http.route('/asterisk_plus/asterisk_ping', type='http', auth='none')
    def asterisk_ping(self):
        with registry('odoopbx_14').cursor() as cr:
            env = Environment(cr, SUPERUSER_ID, {})
            try:
                res = env['asterisk_plus.server'].browse(1).asterisk_ping()
                return '{}'.format(res)
            except Exception as e:
                logger.exception('Error')
                return '{}'.format(e)

    @http.route('/asterisk_plus/ping', type='http', auth='none')
    def ping(self):
        with registry('odoopbx_14').cursor() as cr:
            env = Environment(cr, http.request.env.ref('base.user_admin').id, {})
            try:
                res = env['asterisk_plus.server'].browse(1).ping()
                return http.Response('{}'.format(res))
            except Exception as e:
                logger.exception('Error')
                return '{}'.format(e)

    def check_ip(self, db=None):
        if db:
            with registry(db).cursor() as cr:
                env = Environment(cr, SUPERUSER_ID, {})
                allowed_ips = env[
                    'asterisk_common.settings'].sudo().get_param(
                    'permit_ip_addresses')
        else:
            allowed_ips = http.request.env[
                'asterisk_common.settings'].sudo().get_param(
                'permit_ip_addresses')
        if allowed_ips:
            remote_ip = http.request.httprequest.remote_addr
            if remote_ip not in [
                    k.strip(' ') for k in allowed_ips.split(',')]:
                return BadRequest(
                    'Your IP address {} is not allowed!'.format(remote_ip))

    def _get_partner_by_number(self, db, number, country_code):
        # If db is passed init env for this db
        dst_partner_info = {'id': None}  # Defaults
        if db:
            try:
                with registry(db).cursor() as cr:
                    env = Environment(cr, SUPERUSER_ID, {})
                    dst_partner_info = env[
                        'res.partner'].sudo().get_partner_by_number(
                        number, country_code)
            except Exception:
                logger.exception('Db init error:')
                return BadRequest('Db error, check Odoo logs')
        else:
            dst_partner_info = http.request.env[
                'res.partner'].sudo().get_partner_by_number(
                number, country_code)
        return dst_partner_info

    @http.route('/asterisk_plus/get_caller_name', type='http', auth='none')
    def get_caller_name(self, **kw):
        db = kw.get('db')
        try:
            self.check_ip(db=db)
            number = kw.get('number').replace(' ', '')  # Strip spaces
            country_code = kw.get('country') or False
            if not number:
                return BadRequest('Number not specified in request')
            logger.debug(
                'CALLER NAME REQUEST FOR NUMBER {} country {}'.format(
                    number, country_code))
            dst_partner_info = self._get_partner_by_number(
                db, number, country_code)
            if dst_partner_info['id']:
                return dst_partner_info['name']
            return ''
        except Exception as e:
            logger.exception('Error:')
            if 'request not bound to a database' in str(e):
                return 'db_not_specified'
            elif 'database' in str(e) and 'does not exist' in str(e):
                return 'db_not_exists'
            else:
                return 'Error'

    @http.route('/asterisk_plus/get_partner_manager', auth='public')
    def get_partner_manager(self, **kw):
        db = kw.get('db')
        try:
            self.check_ip(db=db)
            number = kw.get('number').replace(' ', '')  # Strip spaces
            country_code = kw.get('country') or False
            if not number:
                return BadRequest('Number not specified in request')
            dst_partner_info = self._get_partner_by_number(
                db, number, country_code)
            if dst_partner_info['id']:
                # Partner found, get manager.
                partner = http.request.env['res.partner'].sudo().browse(
                    dst_partner_info['id'])
                if partner.user_id:
                    # We have sales person set let check if he has extension.
                    if partner.user_id.asterisk_channel:
                        # We have user configured so let return his exten
                        result = partner.user_id.asterisk_channel
                        logger.info(
                            "Returning partner %s manager's channel %s",
                            partner.name, result)
                        return result
            return ''
        except Exception as e:
            logger.exception('Error:')
            if 'request not bound to a database' in str(e):
                return 'db_not_specified'
            elif 'database' in str(e) and 'does not exist' in str(e):
                return 'db_not_exists'
            else:
                return 'Error'

    @http.route('/asterisk_plus/get_caller_tags', auth='none', type='http')
    def get_caller_tags(self, **kw):
        db = kw.get('db')
        try:
            self.check_ip(db=db)
            number = kw.get('number').replace(' ', '')  # Strip spaces
            country_code = kw.get('country') or False
            if not number:
                return BadRequest('Number not specified in request')
            dst_partner_info = self._get_partner_by_number(
                db, number, country_code)
            if dst_partner_info['id']:
                # Partner found, get manager.
                partner = http.request.env['res.partner'].sudo().browse(
                    dst_partner_info['id'])
                if partner:
                    return ','.join([k.name for k in partner.category_id])
            return ''
        except Exception as e:
            logger.exception('Error:')
            if 'request not bound to a database' in str(e):
                return 'db_not_specified'
            elif 'database' in str(e) and 'does not exist' in str(e):
                return 'db_not_exists'
            else:
                return 'Error'
