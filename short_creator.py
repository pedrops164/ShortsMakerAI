import cv2
import numpy as np
import moviepy.editor as mp
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.io.ImageSequenceClip import ImageSequenceClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.audio.AudioClip import CompositeAudioClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.video.VideoClip import ImageClip
import moviepy.audio.fx.all as afx

target_width, target_height = 576, 1024  # 9:16 aspect ratio

class ShortCreator:

    def __init__(self):
        self.background_video = None
        self.background_music = None
        self.image_audio_pairs = []  # List to store (image_path, audio_path) tuples

    def add_background_music(self, audio_path):
        """
        Add background music to the video.
        """
        self.background_music = AudioFileClip(audio_path)
        self.background_music = self.background_music.fx(afx.volumex, 0.3)  # Reduce volume


    def add_background_video(self, video_path):
        """
        Set the background video.
        """
        #self.background_video = VideoFileClip(video_path).resize(height=1920, width=1080)
        video = VideoFileClip(video_path, audio=False)
        original_width, original_height = video.size

        # Calculate the cropping region
        video_aspect = original_width / original_height
        target_aspect = target_width / target_height

        if video_aspect > target_aspect:
            # Video is wider than 9:16 -> Crop width
            new_width = int(original_height * target_aspect)
            new_height = original_height
        else:
            # Video is taller than 9:16 -> Crop height
            new_width = original_width
            new_height = int(original_width / target_aspect)

        x1 = (original_width - new_width) // 2
        y1 = (original_height - new_height) // 2
        x2 = x1 + new_width
        y2 = y1 + new_height

        # Crop and resize to target resolution
        video = video.crop(x1=x1, y1=y1, x2=x2, y2=y2).resize((target_width, target_height))

        self.background_video = video.set_position("center")

    def add_image_audio_pair(self, image_path, audio_path):
        """
        Add an image-audio pair to the sequence.
        """
        self.image_audio_pairs.append((image_path, audio_path))

    def create_video(self, output_path="output.mp4"):
        """
        Generate the final short video with all the added components.
        """
        if self.background_video is None:
            raise ValueError("Background video not set.")
        
        clips = []
        current_time = 0  # Track timing
        
        for image_path, audio_path in self.image_audio_pairs:
            audio_clip = AudioFileClip(audio_path)
            image_clip = ImageClip(image_path, duration=audio_clip.duration)
            
            # Resize image proportionally so that width is 70% of video width
            aspect_ratio = image_clip.size[1] / image_clip.size[0]  # Height / Width
            image_target_width = int(0.7 * target_width)  # 70% of video width
            image_target_height = int(image_target_width * aspect_ratio)  # Maintain aspect ratio
            image_clip = image_clip.resize(width=image_target_width, height=image_target_height)
            
            # Position the image in the center
            image_clip = image_clip.set_position(("center"))
            image_clip = image_clip.set_audio(audio_clip) # associate audio to image
            image_clip = image_clip.set_start(current_time) # set the start of the clip
            
            clips.append(image_clip)
            
            # Update time for next image-audio pair
            current_time += audio_clip.duration
        
        # randomly sample background video clip from the background video
        # we do it here because we know all the clips have been added, and thus we know the total duration of the video.
        bg_video_max_start_time = max(0, self.background_video.duration - current_time)
        bg_video_start_time = np.random.uniform(0, bg_video_max_start_time)
        self.background_video = self.background_video.subclip(bg_video_start_time, bg_video_start_time + current_time)
        clips.insert(0, self.background_video)

        # Merge all video clips
        final_video = CompositeVideoClip(clips, size=(target_width, target_height))

        if self.background_music:
            # randomly sample background music clip from the background music
            bg_music_max_start_time = max(0, self.background_music.duration - current_time)
            bg_music_start_time = np.random.uniform(0, bg_music_max_start_time)
            self.background_music = self.background_music.subclip(bg_music_start_time, bg_music_start_time + current_time)

            audio_with_bg_music = CompositeAudioClip([final_video.audio, self.background_music])
            final_video = final_video.set_audio(audio_with_bg_music)
            # add background music to the list of clips
            #clips.insert(0, self.background_music)
        
        # Set the duration of the final video
        final_video = final_video.set_duration(current_time)
        
        # Write output video
        final_video.write_videofile(output_path, codec="libx264", fps=30, audio_codec="aac")
        print("Video creation completed!")