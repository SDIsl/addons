# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2020
from  odoo.addons.asterisk_plus.models.server import Server
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import mute_logger
from psycopg2 import IntegrityError
from unittest.mock import patch, call
from unittest.mock import MagicMock
from odoo.tests import new_test_user


class TestUser(TransactionCase):

    def setUp(self):
        super(TestUser, self).setUp()
        # Mock local_job to emulate Salt API success response.
        Server.local_job = MagicMock()
        # Create a test server.
        self.server = self.env['asterisk_plus.server'].create({
            'name': 'Test server',
            'server_id': 'test server'})

    def test_exten_uniq(self):
        user1 = new_test_user(self.env, login='user1', groups='asterisk_plus.group_asterisk_admin')
        user2 = new_test_user(self.env, login='user2', groups='asterisk_plus.group_asterisk_admin')
        self.env['asterisk_plus.user'].create({
            'exten': '11001',
            'user': user1.id,
        })
        with mute_logger('odoo.sql_db'):
            with self.assertRaises(IntegrityError):
                self.env['asterisk_plus.user'].create({
                    'exten': '11001',
                    'user': user2.id,
                })

    def test_user_uniq(self):
        user1 = new_test_user(self.env, login='user1', groups='asterisk_plus.group_asterisk_admin')
        self.env['asterisk_plus.user'].create({
            'exten': '11001',
            'user': user1.id,
        })
        with mute_logger('odoo.sql_db'):
            with self.assertRaises(IntegrityError):
                self.env['asterisk_plus.user'].create({
                    'exten': '11002',
                    'user': user1.id,
                })

    def test_has_asterisk_plus_group(self):
        user1 = new_test_user(self.env, login='user1', groups='asterisk_plus.group_asterisk_admin')
        user2 = new_test_user(self.env, login='user2', groups='asterisk_plus.group_asterisk_user')
        res1 = self.env['asterisk_plus.user'].with_user(user1).has_asterisk_plus_group()
        res2 = self.env['asterisk_plus.user'].with_user(user2).has_asterisk_plus_group()
        self.assertTrue(res1)
        self.assertTrue(res2)

    def test_get_originate_vars(self):
        user1 = new_test_user(self.env, login='user1', groups='asterisk_plus.group_asterisk_admin')
        user2 = new_test_user(self.env, login='user2', groups='asterisk_plus.group_asterisk_admin')
        # Without originate_vars
        ast_user1 = self.env['asterisk_plus.user'].create({
            'user': user1.id,
            'originate_vars': '',
        })
        # With originate_vars
        ast_user2 = self.env['asterisk_plus.user'].create({
            'user': user2.id,
            'originate_vars': 'var1\nvar2\nvar3',
        })        
        res1 = ast_user1._get_originate_vars()
        res2 = ast_user2._get_originate_vars()
        self.assertFalse(res1)
        self.assertEqual(res2, ['var1', 'var2', 'var3'])

    def test_dial_user(self):
        test_user = self.env.user
        ast_user = self.env['asterisk_plus.user'].create({
            "exten": '2222',
            "user": test_user.id,
            "server": self.server.id
        })
        ch1 = self.env['asterisk_plus.user_channel'].create({
            "asterisk_user": ast_user.id,
            "name": "SIP/0001",
            "originate_context": "test-context",
        })
        ast_user.with_context(no_commit=True).dial_user()
        self.assertEqual(self.server.local_job.call_count, 1)
        call1 = self.server.local_job.mock_calls[0]
        _, _, kwargs1 = call1
        action1 = kwargs1['arg'][0]
        self.assertEqual(action1['Channel'], 'SIP/0001')

    def test_open_user_form(self):
        # Admin user
        user1 = new_test_user(self.env, login='user1', groups='asterisk_plus.group_asterisk_admin')
        res = self.env['asterisk_plus.user'].with_user(user1).open_user_form()
        self.assertEqual(res.get('name'), 'Users')
        # User without asterisk_plus.user linked
        user2 = new_test_user(self.env, login='user2', groups='asterisk_plus.group_asterisk_user')
        with self.assertRaises(ValidationError):
            self.env['asterisk_plus.user'].with_user(user2).open_user_form()
        # User with asterisk_plus.user linked
        user3 = new_test_user(self.env, login='user3', groups='asterisk_plus.group_asterisk_user')
        ast_user = self.env['asterisk_plus.user'].create({
            'user': user3.id,
        })
        res = self.env['asterisk_plus.user'].with_user(user3).open_user_form()
        self.assertEqual(res.get('res_id'), ast_user.id)
