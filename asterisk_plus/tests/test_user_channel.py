# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2020
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import mute_logger
from psycopg2 import IntegrityError
from odoo.tests import new_test_user


class TestUserChannel(TransactionCase):

    def setUp(self):
        super(TestUserChannel, self).setUp()
        
        self.test_user = new_test_user(self.env, login='test', groups='asterisk_plus.group_asterisk_user')
        self.asterisk_user = self.env['asterisk_plus.user'].create({
            'user': self.test_user.id,
        })
        self.server = self.asterisk_user.server

    def test_sql_constraint_server_channel_uniq(self):
        self.env['asterisk_plus.user_channel'].create({
                'name': 'SIP/100',
                'asterisk_user': self.asterisk_user.id,
                'server': self.server.id,
            })
        with mute_logger('odoo.sql_db'):
            with self.assertRaises(IntegrityError):
                self.env['asterisk_plus.user_channel'].create({
                    'name': 'SIP/100',
                    'asterisk_user': self.asterisk_user.id,
                    'server': self.server.id,
                })

    def test_channel_name_constraint(self):
        with self.assertRaises(Exception):
            self.env['asterisk_plus.user_channel'].create({
                'name': 'SIP / 100',
                'asterisk_user': self.asterisk_user.id,
            })
    
    def test_user_change_prohibited_field(self):
        user_channel = self.env['asterisk_plus.user_channel'].create({
                'name': 'SIP/100',
                'asterisk_user': self.asterisk_user.id,
            })
        with self.assertRaises(ValidationError):
            user_channel.with_user(self.test_user).write({
                'originate_context': 'test-context',
            })
