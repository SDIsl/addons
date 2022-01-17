# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2020
from odoo import fields, models


class CallsCrmSettings(models.Model):
    _inherit = 'asterisk_plus.settings'

    auto_create_leads_from_calls = fields.Boolean(
        string='Create Leads on Incoming Calls')
    auto_create_leads_missed_calls_only = fields.Boolean(
        string='Only for Missed Calls', default=True)
    auto_create_leads_sales_person = fields.Many2one(
        'res.users',
        domain=[('share', '=', False)],
        string='Default Salesperson')
