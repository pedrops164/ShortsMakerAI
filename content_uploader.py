
from content_manager import ContentManager
from templates import RedditThread
import os
import praw
import subprocess

def get_top_threads(subreddit, topn):
    client_id = os.getenv('REDDIT_CLIENT_ID')
    client_secret = os.getenv('REDDIT_CLIENT_SECRET')
    reddit = praw.Reddit(client_id=client_id, client_secret=client_secret, user_agent='USER_AGENT')
    subreddit = reddit.subreddit(subreddit)
    top_threads = subreddit.top(limit=topn, time_filter='day')
    top_threads_no_nsfw = [thread for thread in top_threads if not thread.over_18]
    return top_threads_no_nsfw

def run():
    # This function runs every 24 hours
    contentManager = ContentManager.get_instance()
    # fetches the top 10 threads from the 'askreddit' subreddit
    top_threads = get_top_threads('askreddit', 15)

    # for each thread link, it creates a RedditThread object and generates a short story
    for thread in top_threads:
        if contentManager.has_processed(thread.url):
            print(f'Skipping (already processed): {thread.url}')
            continue
        print('Processing thread:', thread.url)
        # creates a RedditThread object
        reddit_thread = RedditThread('bg_videos/minecraft3.mp4', thread_object=thread)
        # generates a short story for the Reddit thread, and gets the path of the generated video
        video_file_path, video_title, video_filename = reddit_thread.generate_short()
        print(f'Short story generated for Reddit thread {thread.url} in path {video_file_path}, with title {video_title}')
        
        # --- Call the TikTok uploader script here ---
        # Example of calling: python cli.py upload --user <username> -v <video_filename> -t <video_title>
        try:
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
        except subprocess.CalledProcessError as e:
            print("Error running the TikTok upload script:", e)
            # Depending on your workflow, you might want to skip marking processed if upload fails
            continue

        # marks the thread link as processed
        contentManager.mark_processed(thread.url)

import time
import schedule
if __name__ == '__main__':
    run()
    schedule.every(24).hours.do(run)
    while True:
        schedule.run_pending()
        time.sleep(60*5)  # check every 5 minutes