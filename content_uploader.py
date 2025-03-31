
from content_manager import ContentManager
from templates import RedditThread
import os
import praw
import subprocess
from thread_filterer import get_best_subreddit_titles

def get_top_threads(subreddit, topn):
    client_id = os.getenv('REDDIT_CLIENT_ID')
    client_secret = os.getenv('REDDIT_CLIENT_SECRET')
    reddit = praw.Reddit(client_id=client_id, client_secret=client_secret, user_agent='USER_AGENT')
    subreddit = reddit.subreddit(subreddit)
    top_threads = subreddit.top(limit=topn, time_filter='day')
    top_threads_no_nsfw = [thread for thread in top_threads if not thread.over_18]
    return top_threads_no_nsfw

def post_subreddit_daily(subreddit, topn, search_topn, time_filter):
    # This function fetches the top threads from a subreddit, creates the short form videos and posts them on tiktok
    contentManager = ContentManager.get_instance()
    top_threads = get_best_subreddit_titles(topn, search_topn, subreddit, time_filter)

    for thread in top_threads:
        if contentManager.has_processed(thread.url):
            print(f'Skipping (already processed): {thread.url}')
            continue
        print('Processing thread:', thread.url)
        reddit_thread = RedditThread('bg_videos/minecraft3.mp4', thread_object=thread)
        video_file_path, video_title, video_filename = reddit_thread.generate_short()
        print(f'Short story generated for Reddit thread {thread.url} in path {video_file_path}, with title {video_title}')
        
        try:
            post_tiktok_video(video_title, video_filename)
        except subprocess.CalledProcessError as e:
            print("Error running the TikTok upload script:", e)
            continue

        contentManager.mark_processed(thread.url)

def run():
    post_subreddit_daily('AmItheAsshole', 5, 10, 'week')
    post_subreddit_daily('AskReddit', 10, 50, 'day')
    post_subreddit_daily('relationship_advice', 5, 10, 'week')
    post_subreddit_daily('tifu', 5, 10, 'week')

def post_tiktok_video(video_title, video_filename):
    # --- Call the TikTok uploader script here ---
    # Example of calling: python cli.py upload --user <username> -v <video_filename> -t <video_title>
    cmd = [
        "python.exe",
        "cli.py",
        "upload",
        "--user",
        os.getenv('TIKTOK_USERNAME'),
        "-v",
        video_filename,
        "-t",
        video_title
    ]
    # Run in 'TiktokAutoUploader' directory
    result = subprocess.run(cmd, cwd="TiktokAutoUploader", check=True)
    print("TikTok upload script completed.")
    print(result.stdout)
    print(result.stderr)


import time
import schedule
if __name__ == '__main__':
    run()
    schedule.every(24).hours.do(run)
    while True:
        schedule.run_pending()
        time.sleep(60*5)  # check every 5 minutes