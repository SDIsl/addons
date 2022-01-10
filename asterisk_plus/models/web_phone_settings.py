# -*- coding: utf-8 -*-
from odoo import fields, models


class WebPhoneSettings(models.Model):
    _name = 'asterisk_plus.web_phone_settings'
    _description = 'Web Phone Settings'

    name = fields.Char(default='Web Phone Settings')
    web_phone_sip_protocol = fields.Char(string="SIP Protocol", default='udp')
    web_phone_sip_proxy = fields.Char(string="SIP Proxy")
    web_phone_websocket = fields.Char(string="Websocket")
    web_phone_stun_server = fields.Char(string="Stun Server", default='stun.l.google.com:19302')

    def open_settings_form(self):
        rec = self.env['asterisk_plus.web_phone_settings'].search([])
        if not rec:
            rec = self.sudo().create({})
        else:
            rec = rec[0]
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'asterisk_plus.web_phone_settings',
            'res_id': rec.id,
            'name': 'Web Phone Settings',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
        }
