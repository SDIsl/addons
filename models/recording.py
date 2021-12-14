import base64
from datetime import datetime, timedelta
import io
import time
import wave
import logging
from odoo import models, fields, api, _
from .server import debug

logger = logging.getLogger(__name__)

try:
    import lameenc
    LAMEENC = True
except ImportError:
    logger.info('MP3 encoding not available. '
                'To enable pip3 install lameenc.')
    LAMEENC = False
try:
    import speech_recognition as sr
    SR = True
except ImportError:
    logger.error('Recording speech recognition not available. '
                 'To enable pip3 install SpeechRecognition.')
    SR = False


class Recording(models.Model):
    _name = 'asterisk_plus.recording'
    _description = 'Recording'
    _rec_name = 'uniqueid'
    _order = 'id desc'

    uniqueid = fields.Char(size=64, index=True, readonly=True)
    call = fields.Many2one('asterisk_plus.call', ondelete='set null', readonly=True)
    channel = fields.Many2one('asterisk_plus.channel', ondelete='set null', readonly=True)
    partner = fields.Many2one('res.partner', ondelete='set null', readonly=True)
    calling_user = fields.Many2one('res.users', ondelete='set null', readonly=True)
    called_user = fields.Many2one('res.users', ondelete='set null', readonly=True)
    calling_number = fields.Char(index=True, readonly=True)
    calling_name = fields.Char(compute='_get_calling_name', readonly=True)
    called_number = fields.Char(index=True, readonly=True)
    answered = fields.Datetime(index=True, readonly=True)
    duration = fields.Integer(related='call.duration', store=True)
    recording_widget = fields.Char(compute='_get_recording_widget',
                                   string='Recording')
    recording_filename = fields.Char(readonly=True, index=True)
    recording_data = fields.Binary(readonly=True, string=_('Download'))
    transcript = fields.Text(string='Transcript')
    file_path = fields.Char(readonly=True)

    def _get_recording_widget(self):
        for rec in self:
            rec.recording_widget = '<audio id="sound_file" preload="auto" ' \
                'controls="controls"> ' \
                '<source src="/web/content?model=asterisk_plus.recording&' \
                'id={recording_id}&filename={filename}&field={source}&' \
                'filename_field=recording_filename&download=True" />' \
                '</audio>'.format(
                    recording_id=rec.id,
                    filename=rec.recording_filename,
                    source='recording_data')

    @api.model
    def save_call_recording(self, event):
        uniqueid = event.get('Uniqueid')
        # Check if we have MIXMONITOR event.
        # This is called a few seconds after call Hangup, so filter calls
        # by time first.
        recently = datetime.utcnow() - timedelta(seconds=60)        
        found = self.env['asterisk_plus.channel'].search(
            [('create_date', '>=', recently.strftime('%Y-%m-%d %H:%M:%S')),
             ('uniqueid', '=', uniqueid)], limit=1)
        if not found:
            debug(self, 'Recording was not activated for '
                        'channel {}'.format(found.channel))
            return False
        if not found.recording_file_path:
            debug(self, 'File path not specified for channel {}'.format(found.channel))
            return False
        if found.cause != '16':
            debug(self, 
                'Call Recording was activated but call was not answered'
                ' on {}'.format(found.channel))
            return False
        debug(self, 'Save call recording for channel {}.'.format(found.channel))
        # Transfer the file.
        found.server.local_job(
            fun='asterisk.get_file',
            arg=found.recording_file_path,
            res_model='asterisk_plus.recording',
            res_method='upload_recording',
            pass_back={'channel_id': found.id}
        )
        return True

    @api.model
    def upload_recording(self, data, pass_back):
        channel_id = pass_back.get('channel_id')
        input_data = data.get('file_data')
        if data.get('error'):
            msg = data['error'].get('message', data['error'])
            logger.error('Call recording data error: %s', msg)
            return False
        channel = self.env['asterisk_plus.channel'].browse(channel_id)
        debug(self, 'Call recording upload for channel {}'.format(
            channel.channel))
        mp3_encode = self.env['asterisk_plus.settings'].get_param(
            'use_mp3_encoder')
        transcipt_recording = self.env['asterisk_plus.settings'].get_param(
            'transcipt_recording')
        # Transcript
        transcript = None
        if SR and transcipt_recording:
            debug(self, 'Transcript call recording for channel {}'.format(
                channel.channel))
            key = self.env['asterisk_plus.settings'].get_param(
                'google_sr_api_key') or None
            lang = self.env['asterisk_plus.settings'].get_param(
                'recognition_lang')
            r = sr.Recognizer()
            decoded_input = base64.b64decode(input_data)
            audio_file = sr.AudioFile(io.BytesIO(decoded_input))
            with audio_file as src:
                r.adjust_for_ambient_noise(src, duration=0.5)
                audio = r.record(src)
            try:
                transcript = r.recognize_google(audio, key=key, language=lang)
            except Exception as e:
                logger.error('Speech Recognition error: {}'.format(e))
                transcript = ''
            transcript = transcript
        # Convert to mp3
        if LAMEENC and mp3_encode:
            bit_rate = int(self.env['asterisk_plus.settings'].get_param(
                'mp3_encoder_bitrate', default=96))
            quality = int(self.env['asterisk_plus.settings'].get_param(
                'mp3_encoder_quality', default=4))
            decoded_input = base64.b64decode(input_data)
            output_data = base64.b64encode(
                self._wav_to_mp3(io.BytesIO(decoded_input), bit_rate, quality))
            extension = 'mp3'
        else:
            output_data = input_data
            extension = 'wav'
        # Create a recording
        rec = self.create({
            'uniqueid': channel.uniqueid,
            'recording_data': output_data,
            'recording_filename': '{}.{}'.format(channel.uniqueid, extension),
            'call': channel.call.id,
            'channel': channel.id,
            'partner': channel.call.partner.id,
            'calling_user': channel.call.calling_user.id,
            'called_user': channel.call.called_user.id,
            'calling_number': channel.call.calling_number,
            'called_number': channel.call.called_number,
            'answered': channel.call.answered,
            'transcript': transcript,
            'file_path': channel.recording_file_path,
        })
        # Delete recording from the Asterisk server
        if self.env['asterisk_plus.settings'].get_param('delete_recordings'):
            debug(self, 'DELETE RECORDING {}'.format(rec.file_path))
            channel.server.local_job(
                fun='asterisk.delete_file',
                arg=rec.file_path)
        return True

    def _wav_to_mp3(self, file_data, bit_rate, quality):
        started = time.time()
        wav_data = wave.open(file_data)
        num_channels = wav_data.getnchannels()
        sample_rate = wav_data.getframerate()
        num_frames = wav_data.getnframes()
        pcm_data = wav_data.readframes(num_frames)
        debug(self,
              'Encoding Wave file. Number of channels: '
              '{}. Sample rate: {}, Number of frames: {}'.format(
                num_channels, sample_rate, num_frames))
        wav_data.close()

        encoder = lameenc.Encoder()
        encoder.set_bit_rate(bit_rate)
        encoder.set_in_sample_rate(sample_rate)
        encoder.set_channels(num_channels)
        encoder.set_quality(quality)  # 2-highest, 7-fastest
        mp3_data = encoder.encode(pcm_data)
        mp3_data += encoder.flush()
        logger.info('Recording convert .wav -> .mp3 took %.2f seconds.',
                    time.time() - started)
        return mp3_data
