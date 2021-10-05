# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2020
import logging
import phonenumbers
from phonenumbers import phonenumberutil
from odoo import models, fields, api, tools, _

logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = ['res.partner']

    phone_normalized = fields.Char()
    mobile_normalized = fields.Char()
    phone_extension = fields.Char(help=_(
        'Prefix with # to add 1 second pause before entering. '
        'Every # adds 1 second pause. Example: ###1001'))

    def originate_call(self, number, exten=None):
        """Originate Call to partner.

        Args:
            number (str): Number to dial.
            exten (str): Optional extension number to enter in DTMF mode after answer.
        """
        pass

    def _normalize_phone(self, number):
        """Keep normalized phone numbers in normalized fields.
        """
        self.ensure_one()
        country_code = self._get_country_code()
        try:
            phone_nbr = phonenumbers.parse(number, country_code)
            if phonenumbers.is_possible_number(phone_nbr) or \
                    phonenumbers.is_valid_number(phone_nbr):
                number = phonenumbers.format_number(
                    phone_nbr, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.phonenumberutil.NumberParseException:
            pass
        except Exception as e:
            logger.warning('Normalize phone error: %s', e)
        # Strip the number if parse error.
        number = number.replace(' ', '')
        number = number.replace('(', '')
        number = number.replace(')', '')
        number = number.replace('-', '')
        return number

    def search_by_number(self, number):
        """Search partner by number.
        Args:
            number (str): number to be searched on.
        If several partners are found by the same number:
        a) If partners belong to same company, return company record.
        b) If partners belong to different companies return False.
        """
        pass

    @api.model
    def originate_extension(self, partner_id):
        partner = self.browse(partner_id)
        number = partner.phone_normalized
        extension = partner.phone_extension or ''
        # Minimum 1 second delay.
        dtmf_delay = extension.count('#') or 1
        # Now strip # and have only extension.
        dtmf_digits = extension.strip('#')
        self.env['res.users'].originate_call(
            number, model='res.partner', res_id=partner.id,
            variables={'__dtmf_digits': dtmf_digits,
                       '__dtmf_delay': dtmf_delay})

    def _get_country_code(self):
        partner = self
        if partner and partner.country_id:
            # Return partner country code
            return partner.country_id.code
        elif partner and partner.parent_id and partner.parent_id.country_id:
            # Return partner's parent country code
            return partner.parent_id.country_id.code
        elif partner and partner.company_id and partner.company_id.country_id:
            # Return partner's company country code
            return partner.company_id.country_id.code
        elif self.env.user and self.env.user.company_id.country_id:
            # Return Odoo's main company country
            return self.env.user.company_id.country_id.code
