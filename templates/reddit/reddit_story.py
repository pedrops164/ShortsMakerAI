from templates.content_template import ContentTemplate
from web_scraper import scrape_reddit_story
from short_creator import ShortCreator
import os

# set output path for screenshots
output_path = os.path.join('output', 'reddit_scary_story.mp4')

class RedditScaryStory(ContentTemplate):
    def __init__(self, thread_link):
        self.thread_link = thread_link

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
        scrape_reddit_story(self.thread_link, short_creator=short_creator, emotions=scary_emotions)
        short_creator.add_background_video('bg_videos/creepy/scary2.mp4')
        short_creator.add_background_music('bg_audios/creepy/scary1_long.mp3')
        short_creator.create_video(output_path)
        print('Short story generated for Reddit thread:', self.thread_link)