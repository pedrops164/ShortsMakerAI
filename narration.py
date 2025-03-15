import os
from zyphra import ZyphraClient
from dotenv import load_dotenv
load_dotenv()
import base64
from requests.exceptions import ChunkedEncodingError

def get_wav_as_base64(wav_file_path):
    with open(wav_file_path, "rb") as wav_file:
        return base64.b64encode(wav_file.read())

def create_audio_file(text, output_path, emotions={}, voice_clone_path_wav="./voice_samples/pixabay_generic_epic_trailer.mp3"):
    # get key to zyphros tts api
    zyphra_key = os.environ.get('ZYPHRA_KEY')
    # check if key is set
    if not zyphra_key:
        raise Exception('Zyphra key not set')
    
    client = ZyphraClient(zyphra_key)

    # Text-to-speech
    base_64_voice_clone = get_wav_as_base64(voice_clone_path_wav)
    try:
        audio_data = client.audio.speech.create(
            text=text,
            speaking_rate=20,
            output_path=output_path,
            emotion=emotions,
            speaker_audio=base_64_voice_clone,
            mime_type="audio/mp3",
            model="zonos-v0.1-transformer"  # Default model
        )
    except ChunkedEncodingError:
        raise Exception('Zyphra API request failed')

if __name__ == '__main__':
    create_audio_file('Test speech synthesis', 'output.mp3')