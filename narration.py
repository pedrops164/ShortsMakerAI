import os
from openai import OpenAI
from zyphra import ZyphraClient
from dotenv import load_dotenv
load_dotenv()
import base64
from requests.exceptions import ChunkedEncodingError

def get_wav_as_base64(wav_file_path):
    with open(wav_file_path, "rb") as wav_file:
        return base64.b64encode(wav_file.read()).decode('utf-8')

class Narrator:
    def __init__(self, voice_clone_path_wav="./voice_samples/voice_zonos_gb_male.wav", zyphra_emotions={}):
        self.voice_clone_path_wav = voice_clone_path_wav
        if os.environ.get('TTS_PROVIDER') == 'zyphra':
            self.emotions = zyphra_emotions
            # get key to zyphros tts api
            zyphra_key = os.environ.get('ZYPHRA_KEY')
            # check if key is set
            if not zyphra_key:
                raise Exception('Zyphra api key not set')
            self.client = ZyphraClient(zyphra_key)
        elif os.environ.get('TTS_PROVIDER') == 'openai':
            # get key to openai tts api
            openai_key = os.environ.get('OPENAI_KEY')
            # check if key is set
            if not openai_key:
                raise Exception('OpenAI api key not set')
            self.client = OpenAI(api_key=openai_key)
        else:
            raise Exception('TTS provider not set')

    def create_audio_file(self, text, output_path):

        # Text-to-speech
        base_64_voice_clone = get_wav_as_base64(self.voice_clone_path_wav)
        try:
            if os.environ.get('TTS_PROVIDER') == 'openai':
                audio_data = self.client.audio.speech.create(
                    input=text,
                    model='tts-1',
                    voice='onyx',
                    response_format='mp3',
                    speed=1
                )
                audio_data.write_to_file(output_path)
            elif os.environ.get('TTS_PROVIDER') == 'zyphra':
                audio_data = self.client.audio.speech.create(
                    text=text,
                    speaking_rate=20,
                    output_path=output_path,
                    emotion=self.emotions,
                    speaker_audio=base_64_voice_clone,
                    mime_type="audio/mp3",
                    model="zonos-v0.1-transformer"  # Default model
                )
            else:
                raise Exception('TTS provider not set')
        except ChunkedEncodingError:
            raise Exception('Zyphra API request failed')

if __name__ == '__main__':
    narrator = Narrator()
    narrator.create_audio_file('Test speech synthesis', 'output.mp3')