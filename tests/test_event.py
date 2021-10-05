# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2020

from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import mute_logger
from psycopg2 import IntegrityError


class TestEvent(TransactionCase):

    def setUp(self):
        super(TestEvent, self).setUp()

    def test_create(self):
        test_event = self.env['asterisk_plus.event'].create({
            'source': 'AMI',
            'name': 'Test Event',
            'model': 'asterisk_plus.server',
            'method': 'test_method',
            'delay': 0.0,
            'is_enabled': True,
            'condition': ''
        })
        self.assertTrue(test_event, 'Event creation should be possible!')

    def test_write(self):
        event = self.env['asterisk_plus.event'].create({
            'source': 'AMI',
            'name': 'Test Event Updatable',
            'model': 'asterisk_plus.server',
            'method': 'test_method',
            'delay': 0.0,
            'is_enabled': True,
            'condition': '',
            'update': 'yes',
        })
        event_locked = self.env['asterisk_plus.event'].create({
            'source': 'AMI',
            'name': 'Test Event Locked',
            'model': 'asterisk_plus.server',
            'method': 'test_method',
            'delay': 0.0,
            'is_enabled': True,
            'condition': '',
            'update': 'no',
        })
        event.condition = 'New value'
        event_locked.condition = 'New value'
        self.assertEqual(event.condition, 'New value')
        self.assertEqual(event_locked.condition, '')

    def test_sql_constraint_event_uniq(self):
        self.env['asterisk_plus.event'].create({
            'source': 'AMI',
            'name': 'Test Event',
            'model': 'asterisk_plus.server',
            'method': 'test_method',
        })
        with mute_logger('odoo.sql_db'):
            with self.assertRaises(IntegrityError):
                self.env['asterisk_plus.event'].create({
                    'source': 'AMI',
                    'name': 'Test Event',
                    'model': 'asterisk_plus.server',
                    'method': 'test_method',
                })

    def test_get_icon(self):
        event = self.env['asterisk_plus.event'].create({
            'source': 'AMI',
            'name': 'Test Event Updatable',
            'model': 'asterisk_plus.server',
            'method': 'test_method',
            'delay': 0.0,
            'is_enabled': True,
            'condition': '',
            'update': 'yes',
        })
        event_locked = self.env['asterisk_plus.event'].create({
            'source': 'AMI',
            'name': 'Test Event Locked',
            'model': 'asterisk_plus.server',
            'method': 'test_method',
            'delay': 0.0,
            'is_enabled': True,
            'condition': '',
            'update': 'no',
        })
        self.assertEqual(event.icon, '<span class="fa fa-unlock"></span>')
        self.assertEqual(event_locked.icon, '<span class="fa fa-lock"></span>')
