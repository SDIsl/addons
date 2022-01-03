import json
import logging
from odoo import models, fields, api, _

logger = logging.getLogger(__name__)


class ProjectCall(models.Model):
    _name = 'asterisk_plus.call'
    _inherit = 'asterisk_plus.call'

    ref = fields.Reference(selection_add=[
        ('project.task', 'Tasks'),
        ('project.project', 'Projects')])

    def update_reference(self):
        res = super(ProjectCall, self).update_reference()
        if not res:
            # No reference was set, so we have a change to set it to a task or project
            if self.partner:
                task = self.env['project.task'].search([
                    ('partner_id', '=', self.partner.id)], limit=1)
                project = self.env['project.project'].search([
                    ('partner_id', '=', self.partner.id)], limit=1)
            if task:
                self.ref = task
                return True
            elif project:
                self.ref = project
                return True
