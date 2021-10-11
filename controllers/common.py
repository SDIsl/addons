import re
import functools
import logging
from odoo import http, SUPERUSER_ID, registry
from odoo.api import Environment
from werkzeug.exceptions import BadRequest, Unauthorized, Forbidden
from psycopg2 import OperationalError
from werkzeug.wrappers.response import Response

logger = logging.getLogger(__name__)


def request_wrapper(method):
    """
    wraps controller passed kwargs and before pass to method checks current state
    if accrues some exception, will return corresponding value and status code
    :param method: decorated method
    :return: method with ControllerCommon instance and partner info record
             common: ControllerCommon instance
             dst_partner_info: Partner info base on record
    """
    @functools.wraps(method)
    def inner(self, **kwargs):
        common = ControllerCommon(kwargs)
        try:
            checked = common.check_ip()
        except OperationalError as e:
            return Response(str(e), status=400)
        except Exception as e:
            logger.debug(e)
            return Response('Error', status=400)
        if not isinstance(checked, bool):
            return Response(checked, status=403)
        if not common.number:
            return Response('Number not specified in request', status=400)
        dst_partner_info = common.get_partner_by_number()
        ret_fn = method(self, common, dst_partner_info, **kwargs)
        # can be handled returned value e.g  log before returning response
        return ret_fn

    return inner


class ControllerCommon:
    def __init__(self, kw: dict):
        """
        automatically sets private attribute based on kw passed
        :param kw: dict {
            'country': str,
            'db': str,
            'number': str,
        }
        """
        self._connection_handler = self.ConnectionHandler
        self._remote_ip = None
        if isinstance(kw, dict) and kw:
            for k, v in kw.items():
                setattr(self, f'_{k}', v)

    class ConnectionHandler:
        def __init__(self, db):
            self.db = db

        def __enter__(self):
            """
            recreate context manager which returns correct handler based on _db instance attribute
            :return: environment
            """
            if self.db:
                self._cr = registry(self.db).cursor()
                self._env = Environment(self._cr, SUPERUSER_ID, {})
                return self._env
            return http.request.env

        def __exit__(self, exc_type, exc_value, exc_traceback):
            """
            if cursor was used we need to close it when code is  out of context manager and put it back
            :param exc_type:
            :param exc_value:
            :param exc_traceback:
            """
            if getattr(self, '_cr', None):
                if exc_type:
                    self._cr.rollback()
                self._cr.close()

    def check_ip(self):
        """
        gets correct env handler and checks if ip address is allowed
        :return: bool or str
        """
        with self._connection_handler(self.db) as cr:
            allowed_ips = cr['asterisk_plus.settings'].sudo().get_param(
                'permit_ip_addresses')
            if allowed_ips:
                if self.remote_ip not in [ControllerCommon.sub_string(k) for k in allowed_ips.split(',')]:
                    return 'Your IP address {} is not allowed!'.format(self.remote_ip)
            return True

    def get_partner_by_number(self):
        """
        :return: dict {
            'name': str or defalt value,
            'id': int or default value
        }
        """
        dst_partner_info = {'id': None}  # Defaults
        with self._connection_handler(self.db) as cr:
            dst_partner_info = cr['res.partner'].sudo().get_partner_by_number(
                self.number, self.country_code)
        return dst_partner_info

    @staticmethod
    def sub_string(to_sub: str):
        """
        :param to_sub: str
        :returns removed whitespaces from string if existes
        """
        return re.sub(r"\s+", "", to_sub)

    @property
    def remote_ip(self):
        """
        Make it lazy
        :return: remote ip address
        """
        if self._remote_ip is None:
            self._remote_ip = http.request.httprequest.remote_addr
        return self._remote_ip

    @property
    def db(self):
        """
        :return: db name or None based on instance attribute
        """
        return getattr(self, '_db', None)

    @property
    def number(self):
        """
        :return: number or None based on instance attribute
        """
        number = getattr(self, '_number', None)
        if number is not None:
            return ControllerCommon.sub_string(number)
        return number

    @property
    def country_code(self):
        """
        :return: country code Or None based on instance attribute
        """
        return getattr(self, '_country', None)
