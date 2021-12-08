from odoo import models, fields


class AddNoteWizard(models.TransientModel):
    _name = 'asterisk_plus.add_note_wizard'
    _description = 'Add notes to call'

    notes = fields.Text()

    def add_note(self):
        call = self.env['asterisk_plus.call'].browse(
            self.env.context['active_ids'])
        call.notes = self.notes
