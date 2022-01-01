from odoo.tests.common import HttpCase, new_test_user
import urllib


class TestController(HttpCase):
    def setUp(self, *args, **kwargs):
        res = super().setUp(*args, **kwargs)
        self.user = new_test_user(self.env, login='user', groups='asterisk_plus.group_asterisk_admin')
        self.ast_user = self.env['asterisk_plus.user'].create({
            "exten": 'textext',
            "user": self.user.id,
        })
        self.tags = self.env['res.partner.category'].create([
            {'name': 'tag1'},
            {'name': 'tag2'},
        ])
        self.test_partner = self.env['res.partner'].create({
            'name': 'Test partner',
            'phone': '10101',
            'user_id': self.user.id,
            'category_id': self.tags.ids,
        })
        self.caller_name_url = '/asterisk_plus/get_caller_name/?'
        self.partner_manager_url = '/asterisk_plus/get_partner_manager/?'
        self.caller_tags_url = '/asterisk_plus/get_caller_tags/?'

    def send_request(self, path: str, params: dict):
        return self.url_open("{path}{params}".format(
            path=path,
            params=urllib.parse.urlencode(params)),
            timeout=2)

    def test_forbidden_ip(self):
        with self.subTest(test_name='Forbidden IP'):
            self.env['asterisk_plus.settings'].set_param(
                'permit_ip_addresses', '45.46.47.01')
            res = self.send_request(self.caller_name_url, {'number': '10101'})
            self.assertEqual(res.status_code, 400)

        with self.subTest(test_name='Permitted IP'):
            self.env['asterisk_plus.settings'].set_param(
                'permit_ip_addresses', '')
            res = self.send_request(self.caller_name_url, {'number': '10101'})
            self.assertEqual(res.status_code, 200)

    def test_get_caller_name(self):
        with self.subTest(test_name='Right number passed'):
            res = self.send_request(self.caller_name_url, {'number': '10101'})
            self.assertEqual(res.text, 'Test partner')

        with self.subTest(test_name='Wrong number passed'):
            res = self.send_request(self.caller_name_url, {'number': '10101999'})
            self.assertEqual(res.text, '')

        with self.subTest(test_name='No number passed'):
            res = self.send_request(self.caller_name_url, {})
            self.assertEqual(res.status_code, 200, 'Error')

        with self.subTest(test_name='Wrong DB passed'):
            res = self.send_request(self.caller_name_url, {'number': '10101', 'db': 'wrong_db'})
            self.assertEqual(res.text, 'db_not_exists')
            self.assertEqual(res.status_code, 200, 'db_not_exists')

    def test_get_partner_manager(self):
        with self.subTest(test_name='Partner manager found'):
            self.env['asterisk_plus.user_channel'].create([
                {
                    'name': 'SIP/testssip1',
                    'asterisk_user': self.ast_user.id,
                },
                {
                    'name': 'SIP/testssip2',
                    'asterisk_user': self.ast_user.id,
                },
                {
                    'name': 'SIP/testssip3',
                    'asterisk_user': self.ast_user.id,
                    'originate_enabled': False,
                }])
            res = self.send_request(self.partner_manager_url, {'number': '10101'})
            self.assertEqual(res.text, 'SIP/testssip1&SIP/testssip2')

        with self.subTest(test_name='Partner manager not found'):
            res = self.send_request(self.partner_manager_url, {'number': '10101999'})
            self.assertEqual(res.text, '')

    def test_get_get_caller_tags(self):
        with self.subTest(test_name='Tags found'):
            res = self.send_request(self.caller_tags_url, {'number': '10101'})
            self.assertEqual(res.text, 'tag1,tag2')

        with self.subTest(test_name='Tags not found'):
            res = self.send_request(self.partner_manager_url, {'number': '10101999'})
            self.assertEqual(res.text, '')
