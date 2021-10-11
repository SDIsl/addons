# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2020
import logging
from odoo import http, SUPERUSER_ID, registry
from odoo.api import Environment
from werkzeug.wrappers.response import Response

logger = logging.getLogger(__name__)

from . common import request_wrapper

class AsteriskPlusController(http.Controller):

    @http.route('/asterisk_plus/get_caller_name', type='http', auth='none')
    @request_wrapper
    def get_caller_name(self, common, dst_partner_info, **kwargs):
        logger.debug(
                'CALLER NAME REQUEST FOR NUMBER {} country {}'.format(
                    common.number, common.country_code))
        if dst_partner_info.get('id'):
            return dst_partner_info['name']
        return Response('', status=200)

    @http.route('/asterisk_plus/get_partner_manager', auth='public')
    @request_wrapper
    def get_partner_manager(self, common, dst_partner_info, **kwargs):
        if dst_partner_info.get('id'):
            partner = http.request.env['res.partner'].sudo().browse(
                    dst_partner_info['id'])
            if partner.user_id:
                    # We have sales person set lets check if he has extension.
                    if partner.user_id.asterisk_users:
                        # We have user configured so lets return his exten
                        result = partner.user_id.asterisk_users[0].exten
                        logger.info(
                            "Returning partner %s manager's exten %s",
                            partner.name, result)
                        return Response(result, status=200)
            return Response('', status=200)

    @http.route('/asterisk_plus/get_caller_tags', auth='none', type='http')
    @request_wrapper
    def get_caller_tags(self, common, dst_partner_info, **kwargs):
        if dst_partner_info.get('id'):
            # Partner found, get manager.
            partner = http.request.env['res.partner'].sudo().browse(
                dst_partner_info['id'])
            if partner:
                return Response(','.join([k.name for k in partner.category_id]), status=200)
        return Response('', status=200)

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
