import os
from openai import OpenAI
from zyphra import ZyphraClient
from dotenv import load_dotenv
load_dotenv()
import base64
from requests.exceptions import ChunkedEncodingError
from abc import ABC, abstractmethod
from psola import from_file_to_file
import random

TMP_FOLDER = os.environ.get('TMP_FOLDER')

def get_wav_as_base64(wav_file_path):
    with open(wav_file_path, "rb") as wav_file:
        return base64.b64encode(wav_file.read()).decode('utf-8')

class Narrator(ABC):
    """
    Abstract base class for text-to-speech narration.
    """
    def __init__(self):
        self.audio_index = 0

    @abstractmethod
    def create_audio_file(self, text):
        """
        Create an audio file from the given text and return the file path.
        Subclasses must implement the TTS logic.
        """
        pass
    

class NarratorZyphra(Narrator):
    """
    Zyphra-based narration.
    scary_emotions={
        "happiness": 0.1,
        "neutral": 0.5,
        "sadness": 0.05,
        "anger": 0.05,
        "fear": 0.9,
        "surprise": 0.05,
        "anger": 0.05,
        "other": 0.5
    }
    """
    def __init__(self, voice_clone_path_wav="./voice_samples/voice_zonos_gb_male.wav", zyphra_emotions=None):
        super().__init__()
        self.voice_clone_path_wav = voice_clone_path_wav
        self.emotions = zyphra_emotions or {}
        
        # Validate Zyphra API key
        zyphra_key = os.environ.get('ZYPHRA_KEY')
        if not zyphra_key:
            raise Exception('Zyphra API key not set')

        self.client = ZyphraClient(zyphra_key)

    def create_audio_file(self, text):
        text = text.strip()
        if text and text[-1] not in ('.', '?'):
            text += '.'
        output_path = os.path.join(TMP_FOLDER, f'audio_{self.audio_index}.mp3')
        self.audio_index += 1
        
        try:
            # Convert the voice clone WAV to base64
            base_64_voice_clone = get_wav_as_base64(self.voice_clone_path_wav)
            
            # Perform Zyphra TTS
            self.client.audio.speech.create(
                text=text,
                speaking_rate=20,
                output_path=output_path,
                emotion=self.emotions,
                speaker_audio=base_64_voice_clone,
                mime_type="audio/mp3",
                model="zonos-v0.1-transformer"
            )
            return output_path
        except ChunkedEncodingError:
            raise Exception('Zyphra API request failed')

class NarratorOpenAI(Narrator):
    """
    OpenAI-based narration with post-processing for speed adjustment.
    """
    def __init__(self, voice_actor, speed=1.0):
        super().__init__()
        
        # Validate OpenAI API key
        openai_key = os.environ.get('OPENAI_KEY')
        if not openai_key:
            raise Exception('OpenAI API key not set')

        self.client = OpenAI(api_key=openai_key)
        self.voice_actor = voice_actor
        self.speed = speed
        self.model = 'gpt-4o-mini-tts'  # or 'tts-1'

    def random_openai_voiceactor(self):
        """
        Returns a random OpenAI voice actor from the available list.
        """
        voice_actors = [
            'alloy', 'ash', 'ballad',
            'coral', 'echo', 'fable',
            'nova', 'sage', 'shimmer',
        ]
        return random.choice(voice_actors)

    def change_audio_speed(self, input_path, output_path, speed_factor):
        """
        Adjusts the speed of an audio file without distorting the pitch.
        """
        # Convert to absolute paths
        input_path = os.path.abspath(input_path)
        output_path = os.path.abspath(output_path)

        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        from_file_to_file(input_path, output_path, constant_stretch=speed_factor)

    def create_audio_file(self, text, voice_actor=None):
        text = text.strip()
        if text and text[-1] not in ('.', '?'):
            text += '.'
        
        raw_output_path = os.path.join(TMP_FOLDER, f'audio_{self.audio_index}_raw.mp3')
        final_output_path = os.path.join(TMP_FOLDER, f'audio_{self.audio_index}.mp3')
        self.audio_index += 1

        voice = voice_actor or self.voice_actor

        try:
            # Generate OpenAI TTS audio
            audio_data = self.client.audio.speech.create(
                input=text,
                model=self.model,
                voice=voice,
                response_format='mp3',
                #instructions='You are a narrator who speaks clearly and at a fast pace',
            )
            audio_data.write_to_file(raw_output_path)

            # If speed is different from 1, apply speed adjustment
            if self.speed != 1.0:
                self.change_audio_speed(raw_output_path, final_output_path, self.speed)
                os.remove(raw_output_path)  # Remove the raw file after processing
            else:
                final_output_path = raw_output_path  # No change needed

            return final_output_path
        except ChunkedEncodingError:
            raise Exception('OpenAI API request failed')