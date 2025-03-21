from templates.content_template import ContentTemplate
from web_scraper import scrape_reddit_post, setup_driver_reddit
from short_creator import ShortCreator
import os
from narration import NarratorOpenAI
from util import sanitize_filename

output_dir = 'TiktokAutoUploader/VideosDirPath'

class RedditScaryStory(ContentTemplate):
    def __init__(self, thread_link, bg_video, bg_music):
        self.thread_link = thread_link
        self.bg_video = bg_video
        self.bg_music = bg_music

    def generate_short(self):
        print('Generating short story for Reddit thread:', self.thread_link)
        short_creator = ShortCreator()
        narrator = NarratorOpenAI('onyx')
        driver = setup_driver_reddit(self.thread_link, dark_mode=True)
        title_text, content_texts, header_image_path, content_images_paths = scrape_reddit_post(driver, dark_mode=True, character_threshold=150)
        driver.quit()
        title_narration_path = narrator.create_audio_file(title_text)
        content_narrations_paths = [narrator.create_audio_file(text) for text in content_texts]
        
        # add image audio pair of header to short creator object
        short_creator.add_image_audio_pair(header_image_path, title_narration_path)
        for content_image_path, content_narration_path in zip(content_images_paths, content_narrations_paths):
            # add image audio pair of paragraph group to short creator object
            short_creator.add_image_audio_pair(content_image_path, content_narration_path)

        short_creator.add_background_video(self.bg_video)
        short_creator.add_background_music(self.bg_music)
        title_text_sanitized = sanitize_filename(title_text)
        output_path = os.path.join(output_dir, f'{title_text_sanitized}.mp4')
        short_creator.create_video(output_path)
        print('Short story generated for Reddit thread:', self.thread_link)
        return output_path, title_text