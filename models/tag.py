# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2021
from odoo import models, fields, api, _


class Tag(models.Model):
    _name = 'asterisk_plus.tag'
    _description = 'Recording Tag'

    name = fields.Char(required=True)
    recordings = fields.Many2many('asterisk_plus.recording',
                                  relation='asterisk_plus_recording_tag',
                                  column1='recording', column2='tag')

    @api.model
    def create(self, vals):
        # Delete tags not attached to any recording
        tags = self.sudo().search([])
        tags.filtered(lambda x: len(x.recordings) == 0).unlink()
        return super(Tag, self).create(vals)
