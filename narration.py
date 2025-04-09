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

    def random_voiceactor(self):
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
        

import requests

class NarratorElevenLabs(Narrator):
    """
    ElevenLabs-based narration with voice selection capabilities.
    Uses direct API calls to avoid version compatibility issues.
    """
    def __init__(self, voice_id='pNInz6obpgDQGcFmaJgB', stability=0.5, speed=1.2):
        # voice defaults to Adam with max speed
        super().__init__()
        
        # Validate ElevenLabs API key
        self.api_key = os.environ.get('ELEVENLABS_KEY')
        if not self.api_key:
            raise Exception('ElevenLabs API key not set')
        
        self.voice_id = voice_id  # If None, will use random voice
        self.stability = stability
        self.speed = speed
        self.base_url = "https://api.elevenlabs.io/v1"
        self.available_voices = ['9BWtsMINqrJLrRacOk9x', 'CwhRBWXzGAHq8TQ4Fs17', 'EXAVITQu4vr4xnSDxMaL', 'FGY2WhTYpPnrIDTdsKH5', 'IKne3meq5aSn9XLyUdCD', 'JBFqnCBsd6RMkjVDRZzb', 'N2lVS1w4EtoT3dr4eOWO', 'SAz9YHcvj6GT2YYXdXww', 'TX3LPaxmHKxFdv7VOQHJ', 'XB0fDUnXU5powFXDhCwa', 'Xb7hH8MSUJpSbSDYk0k2', 'XrExE9yKIg1WjnnlVkGX', 'bIHbv24MWmeRgasZH58o', 'cgSgspJ2msm6clMCkdW9', 'cjVigY5qzO86Huf0OWal', 'iP95p4xoKVk53GoZ742B', 'nPczCjzI2devNBz1zQrb', 'onwK4e9ZLuTAKqWW03F9', 'pFZP5JQG7iQjIQuC4Bku', 'pqHfZKP75CvOlQylNhV4']
        
    def get_available_voices(self):
        """
        Fetches available voices from ElevenLabs API using direct HTTP request.
        """
        if self.available_voices is not None:
            return self.available_voices
            
        url = f"{self.base_url}/voices"
        headers = {
            "Accept": "application/json",
            "xi-api-key": self.api_key
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            voices_data = response.json()
            self.available_voices = voices_data.get('voices', [])
            return self.available_voices
        else:
            raise Exception(f"Failed to fetch voices: {response.status_code}, {response.text}")

    def random_voiceactor(self):
        """
        Returns a random ElevenLabs voice ID from the available voices.
        """
        selected_voice_id = random.choice(self.available_voices)
        return selected_voice_id

    def create_audio_file(self, text, voice_actor=None):
        text = text.strip()
        if text and text[-1] not in ('.', '?', '!'):
            text += '.'
        
        output_path = os.path.join(TMP_FOLDER, f'audio_{self.audio_index}.mp3')
        self.audio_index += 1
        
        try:
            # Select voice ID (either specified or random)
            #voice_id = self.voice_id if self.voice_id else self.random_voiceactor()
            voice_id = voice_actor if voice_actor else self.voice_id
            
            # Set up the API request
            url = f"{self.base_url}/text-to-speech/{voice_id}"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }
            
            data = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": self.stability,
                    "speed": self.speed,
                }
            }
            
            # Make the API request
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                # Save the audio to a file
                with open(output_path, "wb") as file:
                    file.write(response.content)
                return output_path
            else:
                raise Exception(f"API request failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            raise Exception(f'ElevenLabs API request failed: {str(e)}')
        
if __name__ == "__main__":
    # Example usage
    narrator = NarratorElevenLabs()
    audio_file = narrator.create_audio_file("Hello, this is a test.")
    print(f"Audio file created at: {audio_file}")