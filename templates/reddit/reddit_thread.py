from templates.content_template import ContentTemplate
from web_scraper import setup_driver_reddit, scrape_reddit_thread
from short_creator import ShortCreator
import os
from narration import NarratorOpenAI
from util import sanitize_filename

output_dir = 'TiktokAutoUploader/VideosDirPath'

class RedditThread(ContentTemplate):
    def __init__(self, thread_link, bg_video, bg_music=None):
        self.thread_link = thread_link
        self.bg_video = bg_video
        self.bg_music = bg_music

    def generate_short(self):
        print('Generating short story for Reddit thread:', self.thread_link)
        short_creator = ShortCreator()
        narrator = NarratorOpenAI('ash', speed=1.25)
        driver = setup_driver_reddit(self.thread_link, dark_mode=True)
        post_title_text, post_content_texts, post_header_image_path, post_content_images_paths, comments_content_paragraphs, comments_content_image_paths = \
            scrape_reddit_thread(driver, dark_mode=True, character_threshold=150, ncomments=5)
        driver.quit()
        title_narration_path = narrator.create_audio_file(post_title_text)
        content_narrations_paths = [narrator.create_audio_file(text) for text in post_content_texts]
        comments_narrations_paths = [[narrator.create_audio_file(text) for text in comment] for comment in comments_content_paragraphs]
        
        # add image audio pair of header to short creator object
        short_creator.add_image_audio_pair(post_header_image_path, title_narration_path)
        for content_image_path, content_narration_path in zip(post_content_images_paths, content_narrations_paths):
            # add image audio pair of paragraph group to short creator object
            print('Adding image audio pair:', content_image_path, content_narration_path)
            short_creator.add_image_audio_pair(content_image_path, content_narration_path)
        for comment_images_paths, comment_narrations_paths in zip(comments_content_image_paths, comments_narrations_paths):
            # comment_images_paths contains images of the current comment
            # comment_narrations_paths contains narrations of the current comment
            for content_image_path, content_narration_path in zip(comment_images_paths, comment_narrations_paths):
                # add image audio pair of paragraph group of comment to short creator object
                print('Adding image audio pair:', content_image_path, content_narration_path)
                short_creator.add_image_audio_pair(content_image_path, content_narration_path)

        short_creator.add_background_video(self.bg_video)
        if self.bg_music:
            short_creator.add_background_music(self.bg_music)
        title_text_sanitized = sanitize_filename(post_title_text)
        video_filename = f'{title_text_sanitized}.mp4'
        output_path = os.path.join(output_dir, video_filename)
        short_creator.create_video(output_path)
        print(f'Short story generated for Reddit thread {self.thread_link} in path {output_path}')
        return output_path, post_title_text, video_filename