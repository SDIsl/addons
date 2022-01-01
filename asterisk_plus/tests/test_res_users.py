# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2020
import json
import logging
from odoo.tests import tagged
#from odoo.addons.asterisk_plus.models.res_users import ResUser
from odoo.tests.common import TransactionCase
from unittest.mock import patch, call


logger = logging.getLogger(__name__)


class ServerTest(TransactionCase):

    def setUp(self, *args, **kwargs):
        res = super().setUp(*args, **kwargs)
        partner = self.env['res.partner'].create({'name': "Test User"})
        self.test_user = self.env['res.users'].create({
            'login': 'testuser',
            'partner_id': partner.id
        })
        return res

    def test_asterisk_plus_notify(self):
        self.test_user.asterisk_plus_notify(
            'Hello frOM TEST', title='PBX TEST', sticky=True, warning=True)
        rec = self.env['bus.bus'].search([], limit=1, order='id desc')
        msg = json.loads(rec.message)
        self.assertEqual(msg['message'], 'Hello frOM TEST')
        self.assertEqual(msg['title'], 'PBX TEST')
        self.assertEqual(msg['sticky'], True)
        self.assertEqual(msg['warning'], True)

