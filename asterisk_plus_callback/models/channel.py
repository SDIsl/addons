import logging
from odoo import models, fields, api
from odoo.addons.asterisk_plus.models.settings import debug

logger = logging.getLogger(__name__)

class CallbackChannel(models.Model):
    _inherit = 'asterisk_plus.channel'

    callback = fields.Many2one(
        'asterisk_plus_callback.callback',
        ondelete='cascade')

    def callback_originate_call_response(self, data, pass_back=None):
        channel = self.env['asterisk_plus.channel'].search([('uniqueid', '=', pass_back['channel_id'])])
        response = data[0].get('Response')
        debug(self, 'Call {} response: {}'.format(channel.channel, response))
        if channel.callback and response == 'Error':
            channel.callback.status = 'failed'
            channel.write({
                'cause_txt': data[0].get('Message'),
                'cause': '0'
            })
        return channel.id

    @api.model
    def on_ami_originate_response_failure(self, event):
        channel_id = super(CallbackChannel, self).on_ami_originate_response_failure(event)
        channel = self.env['asterisk_plus.channel'].with_context(
            active_test=False).browse(channel_id)
        if channel.callback and not channel.cause:
            # If we had a Hangup message no need for failed state.
            channel.callback.status = 'failed'
        return channel_id

    @api.model
    def on_ami_hangup(self, event):
        channel_id = super(CallbackChannel, self).on_ami_hangup(event)
        if channel_id:
            try:
                channel = self.env['asterisk_plus.channel'].browse(channel_id)
                # Check for the situation when channel originate did not succeed normally
                # but it is not a failure (channel busy). In this case both Hangup and 
                # OriginateResponse come but Hangup comes later.
                if channel.callback and channel.callback.status == 'failed' and \
                        channel.cause != '16':
                    # Restore callback status that was set on OriginateResponse.
                    channel.callback.status = 'progress'
                    debug(self, 'Restoring callback status to progress.')                
                elif channel.callback:
                    if event['Cause'] == '16' and not channel.callback.done_by_event:
                        # Normal Clearing, set callback status to done.
                        channel.callback.status = 'done'
                        debug(self, 'Channel {} callback done.'.format(channel.channel))
                    elif event['Cause'] == '16' and channel.callback.done_by_event:
                        debug(self, 'Channel {} ignore normal call clearing as'
                                    ' waiting for done event.'.format(channel.channel))
                    else:
                        debug(self, 'Channel callback {} status not done'.format(channel.channel))
                elif channel.parent_channel.callback:
                    debug(self, 'Not setting done by leg 2 hangup.')
                else:
                    debug(self, 'Channel {} does not belong to callback'.format(channel.channel))
            except Exception:
                logger.exception('Callback on_ami_hangup error')
        return channel_id
