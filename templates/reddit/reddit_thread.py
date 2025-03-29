from templates.content_template import ContentTemplate
from short_creator import ShortCreator
import os
from narration import NarratorOpenAI
from util import sanitize_filename, split_paragraphs_from_text
from image_creator import RedditImageCreator

output_dir = 'TiktokAutoUploader/VideosDirPath'

class RedditThread(ContentTemplate):
    def __init__(self, bg_video, thread_object=None, bg_music=None, ncomments=5):
        self.thread_object = thread_object
        self.bg_video = bg_video
        self.bg_music = bg_music
        self.reddit_image_creator = RedditImageCreator()
        self.ncomments = ncomments

    def _scrape_from_praw(self):
        post_title_text = self.thread_object.title
        content_text = self.thread_object.selftext
        #post_content_texts = [content_text] if content_text.strip() != "" else []
        post_content_texts = split_paragraphs_from_text(content_text) if content_text.strip() != "" else []
        comments_content_paragraphs = [split_paragraphs_from_text(comment.body) for comment in self.thread_object.comments[:self.ncomments]]
        comments_content_paragraphs = []
        comments_content_image_paths = []
        for comment in self.thread_object.comments[:self.ncomments]:
            # get list of paragraphs from comment body, and create image for each paragraph
            comment_paragraphs, comment_images_paths = self.reddit_image_creator.create_comment_text_images_pairs(comment)
            comments_content_paragraphs.append(comment_paragraphs)
            comments_content_image_paths.append(comment_images_paths)
        return post_title_text, post_content_texts, comments_content_paragraphs, comments_content_image_paths

    def generate_short(self):
        print('Generating short story for Reddit thread:', self.thread_object.title)
        short_creator = ShortCreator()
        narrator = NarratorOpenAI('ash', speed=1.25)

        post_title_text, post_content_texts, comments_content_paragraphs, comments_content_image_paths = self._scrape_from_praw()
        post_header_image_path = self.reddit_image_creator.create_reddit_post_gif(post_title_text)
        post_content_images_paths = [self.reddit_image_creator.create_text_image(t, save_image=True)[1] for t in post_content_texts]

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
        print(f'Short story generated for Reddit thread "{self.thread_object.title}" in path {output_path}')
        return output_path, post_title_text, video_filename