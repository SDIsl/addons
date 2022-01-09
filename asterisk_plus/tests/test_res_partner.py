from odoo.tests.common import SavepointCase, TransactionCase
from odoo.tests import new_test_user, Form, tagged
from odoo import tools, _

@tagged('res_partner_test')
class TestResPartner(SavepointCase):
    def test_number(self):
        partner = self.env['res.partner'].create(
            {
                'name': "Test User",
                'phone': "+442083661170",
                'child_ids':
                    [(0, 0, {
                        'name': 'Test Child1',
                        'mobile': '+442083661171',
                    }),
                     (0, 0, {
                         'name': 'Test Child2',
                         'phone': '442083661172',
                         'country_id': self.env['res.country'].search([('code', '=', 'GB')]).id
                     }),
                     (0, 0, {
                         'name': 'Test Child3',
                         'phone': '442083661173',
                         'country_id': self.env['res.country'].search([('code', '=', 'US')]).id
                     }),
                     (0, 0, {
                         'name': 'Test Child4',
                         'mobile': '4420(836)611   74',
                         'country_id': self.env['res.country'].search([('code', '=', 'GB')]).id
                     }),
                     (0, 0, {
                         'name': 'Test Child5',
                         'phone': '4420(836)611   75',
                     })]

            }
        )
        self.assertEqual(partner.phone, partner.phone_normalized)
        self.assertEqual(partner.child_ids.mapped(lambda r: (r.phone_normalized or r.mobile_normalized) in
                                                  ['+442083661171', '+442083661172', '442083661173',
                                                   '+442083661174', '442083661175']), [True, True, True, True, True])

    def test_get_partner_by_name(self):
        no_number = self.env['res.partner'].get_partner_by_number('unknown')
        self.assertEqual({'name': _('Unknown'), 'id': False}, no_number)
        partner = self.env['res.partner'].create({
            'name': "Test User",
            'phone': "+442083661171",
        })
        with_number_1 = partner.get_partner_by_number('+442083661171')
        with_number_2 = partner.get_partner_by_number('442083661171')
        self.assertEqual(all([with_number_1.get('name') == 'Test User', with_number_2.get('name') == 'Test User']), True)

    def test_get_partner_by_number_cache(self):
        no_number = self.env['res.partner'].get_partner_by_number('unknown')
        self.assertEqual({'name': _('Unknown'), 'id': False}, no_number)
        self.env['res.partner'].get_partner_by_number('+442083661171')
        partner = self.env['res.partner'].with_context({'no_clear_cache': True}).create({
            'name': "Test User",
            'phone': "+442083661171",
        })
        self.assertEqual(partner.get_partner_by_number('+442083661171'), {'name': _('Unknown'), 'id': False})
        partner.clear_caches()
        self.assertEqual(partner.get_partner_by_number('+442083661171').get('name'), 'Test User')
        