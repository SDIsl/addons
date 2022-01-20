# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2021
import logging
from odoo import models, fields, api, _
from odoo.addons.asterisk_plus.models.settings import debug

logger = logging.getLogger(__name__)


class CrmCall(models.Model):
    _inherit = 'asterisk_plus.call'

    ref = fields.Reference(selection_add=[('crm.lead', 'Leads')])

    def update_reference(self):
        res = super(CrmCall, self).update_reference()
        if not res:
            lead = None
            # No reference was set, so we have a change to set it to a lead
            debug(self, 'DIRECTION: {}'.format(self.direction))
            if self.direction == 'in':                
                lead = self.env['crm.lead'].get_lead_by_number(self.calling_number)
            else:
                lead = self.env['crm.lead'].get_lead_by_number(self.called_number)
            debug(self, 'LEAD: {}'.format(lead))
            if lead:
                self.ref = lead
                return True

    @api.constrains('is_active', 'direction')
    def auto_create_lead(self):
        auto_create_leads = self.env['asterisk_plus.settings'].get_param(
            'auto_create_leads_from_calls')
        only_missed = self.env[
            'asterisk_plus.settings'].get_param(
            'auto_create_leads_missed_calls_only')
        default_sales_person = self.env[
            'asterisk_plus.settings'].get_param(
            'auto_create_leads_sales_person')
        for rec in self:            
            if not self.direction == 'in' or rec.ref:
                # We only do it for incoming calls without reference.
                continue
            if not rec.is_active:
                # Call end
                if auto_create_leads and only_missed and rec.status != 'answered':
                    debug(self, 'CREATE LEAD FROM MISSED CALL')
                    if self.env.user.has_group('asterisk_plus.group_asterisk_server'):
                        lead = self.env['crm.lead'].sudo().create({
                            'name': rec.calling_name,
                            'type': 'lead',
                            'user_id': rec.called_user.id or default_sales_person.id,
                            'partner_id': rec.partner.id,
                            'phone': rec.calling_number,
                        })
                        rec.ref = lead
            else:
                # Call start
                lead = self.env['crm.lead'].get_lead_by_number(self.calling_number)
                if not lead:
                    if auto_create_leads and not only_missed:
                        debug(self, 'CREATE LEAD FROM CALL START')
                        if self.env.user.has_group('asterisk_plus.group_asterisk_server'):
                            lead = self.env['crm.lead'].sudo().create({
                                'name': rec.calling_name,
                                'type': 'lead',
                                'user_id': rec.called_user.id or default_sales_person.id,
                                'partner_id': rec.partner.id,
                                'phone': rec.calling_number,
                            })
                            rec.ref = lead
                else:
                    # Lead found
                    rec.ref = lead

