from templates.content_template import ContentTemplate
from web_scraper import scrape_reddit_story
from short_creator import ShortCreator
import os
from narration import Narrator

# set output path for screenshots
output_path = os.path.join('output', 'reddit_scary_story.mp4')

class RedditScaryStory(ContentTemplate):
    def __init__(self, thread_link, bg_video, bg_music, voice_clone_file):
        self.thread_link = thread_link
        self.bg_video = bg_video
        self.bg_music = bg_music
        self.voice_clone_file = voice_clone_file

    def generate_short(self):
        print('Generating short story for Reddit thread:', self.thread_link)
        short_creator = ShortCreator()
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
        narrator = Narrator(voice_clone_path_wav=self.voice_clone_file, zyphra_emotions=scary_emotions)
        scrape_reddit_story(self.thread_link, short_creator=short_creator, narrator=narrator, dark_mode=True)
        short_creator.add_background_video(self.bg_video)
        short_creator.add_background_music(self.bg_music)
        short_creator.create_video(output_path)
        print('Short story generated for Reddit thread:', self.thread_link)