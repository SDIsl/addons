# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2020
from odoo.tests import tagged
from  odoo.addons.asterisk_plus.models.server import Server
from odoo.tests.common import TransactionCase
from unittest.mock import patch, call
from unittest.mock import MagicMock
from odoo.tests import new_test_user


class ServerTest(TransactionCase):

    def setUp(self):
        res = super(ServerTest, self).setUp()
        # Mock local_job to emulate Salt API success response.
        Server.local_job = MagicMock()
        # Create a test server.
        self.server = self.env['asterisk_plus.server'].create({
            'name': 'Test',
            'server_id': 'test'
        })
        return res

    def test_ping(self):
        self.server.local_job.return_value = True
        self.assertEqual(self.server.ping(), True)

    def test_ping_reply(self):
        self.server.ping_reply('test', {'uid': 1})
        self.assertEqual(
            self.env['bus.bus'].search([], order='id desc', limit=1).message,
            '{"message":"test","title":"PBX","sticky":false,"warning":false}'
        )

    def test_asterisk_ping(self):
        self.server.local_job.return_value = [{'Response': 'Success'}]
        self.assertEqual(self.server.asterisk_ping(), [{'Response': 'Success'}])

    def test_originate_call(self):
        self.server.local_job.reset_mock()
        test_res_user = new_test_user(
            self.env, login='asterisk_plus_test',
            groups='asterisk_plus.group_asterisk_user',
        )
        ast_user = self.env['asterisk_plus.user'].create({
            "exten": '110011',
            "user": test_res_user.id,
            "server": self.server.id})
        # Create channel 1
        ch1 = self.env['asterisk_plus.user_channel'].create({
            "asterisk_user": ast_user.id,
            "name": "SIP/0001",
            "originate_context": "test-context",
        })
        # Create channel 2
        ch2 = self.env['asterisk_plus.user_channel'].create({
            "asterisk_user": ast_user.id,
            "name": "SIP/0002",
            "originate_context": "test-context",
        })
        # Create channel 3 without originate enabled
        ch3 = self.env['asterisk_plus.user_channel'].create({
            "asterisk_user": ast_user.id,
            "name": "SIP/0003",
            "originate_context": "test-context",
            "originate_enabled": False,
        })
        self.server.with_user(test_res_user).with_context(no_commit=True).originate_call('0000000')
        self.assertEqual(self.server.local_job.call_count, 2)
        call1 = self.server.local_job.mock_calls[0]
        call2 = self.server.local_job.mock_calls[1]
        _, _, kwargs1 = call1
        _, _, kwargs2 = call2
        action1 = kwargs1['arg'][0]
        action2 = kwargs2['arg'][0]
        self.assertEqual(action1['Channel'], 'SIP/0001')
        self.assertEqual(action2['Channel'], 'SIP/0002')

    def test_originate_call_response(self):
        # Test Extension does not exist.
        data = [{
            'Response': 'Error', 
            'ActionID': 'action/38073b0b-df2b-43e6-a254-a0b192739339/1/7836',
            'Message': 'Extension does not exist.',
            'content': ''
        }]
        self.server.originate_call_response(data, pass_back={'uid': 1})
        self.assertEqual(
            self.env['bus.bus'].search([], order='id desc', limit=1).message,
            '{"message":"Extension does not exist.","title":"PBX","sticky":false,"warning":true}'
        )
