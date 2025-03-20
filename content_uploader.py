
from content_manager import ContentManager
from templates import RedditThread
import os
import praw

def get_top_threads_link(subreddit, topn):
    client_id = os.getenv('REDDIT_CLIENT_ID')
    client_secret = os.getenv('REDDIT_CLIENT_SECRET')
    reddit = praw.Reddit(client_id=client_id, client_secret=client_secret, user_agent='USER_AGENT')
    subreddit = reddit.subreddit(subreddit)
    top_threads = subreddit.top(limit=topn, time_filter='day')
    top_threads_link_no_nsfw = [thread.url for thread in top_threads if not thread.over_18]
    return top_threads_link_no_nsfw

def run():
    # This function runs every 24 hours
    contentManager = ContentManager.get_instance()
    # fetches the top 10 threads from the 'askreddit' subreddit
    top_threads_link = get_top_threads_link('askreddit', 15)

    # for each thread link, it creates a RedditThread object and generates a short story
    for thread_link in top_threads_link:
        if contentManager.has_processed(thread_link):
            print(f'Skipping (already processed): {thread_link}')
            continue
        print('Processing thread:', thread_link)
        # creates a RedditThread object
        reddit_thread = RedditThread(thread_link, 'bg_videos/minecraft3.mp4')
        # generates a short story for the Reddit thread, and gets the path of the generated video
        video_file_path, video_title = reddit_thread.generate_short()
        print(f'Short story generated for Reddit thread {thread_link} in path {video_file_path}, with title {video_title}')
        # marks the thread link as processed
        contentManager.mark_processed(thread_link)

if __name__ == '__main__':
    run()