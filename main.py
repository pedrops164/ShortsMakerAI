import sys
from templates import RedditScaryStory, RedditThread
import argparse

def main():
    parser = argparse.ArgumentParser(description="Generate a scary story video based on Reddit content.")
    parser.add_argument("content_type", choices=["ai_pov", "reddit_story", "reddit_thread"], help="Specify the type of content to generate.")
    parser.add_argument("thread_link", nargs="?", help="The Reddit thread link for 'reddit_story' content type.")

    # Additional required arguments for reddit_story
    parser.add_argument("--bg_video", required=False, help="Path to the background video file.")
    parser.add_argument("--bg_music", required=False, help="Path to the background music file.")
    #parser.add_argument("--voice_clone_file", required=False, help="Path to the voice clone file.")

    args = parser.parse_args()
    
    if args.content_type == 'ai_pov':
        print('ai_pov')
    elif args.content_type == 'reddit_story':
        if not args.thread_link:
            print("Error: A Reddit thread link is required for 'reddit_story'.")
            sys.exit(1)

        # Check that all three additional arguments are provided
        if not args.bg_video or not args.bg_music:
            print("Error: --bg_video and --bg_music are required for 'reddit_story'.")
            sys.exit(1)

        reddit_story = RedditScaryStory(args.thread_link, args.bg_video, args.bg_music)
        reddit_story.generate_short()
    elif args.content_type == 'reddit_thread':
        print('reddit_thread')
        if not args.thread_link:
            print("Error: A Reddit thread link is required for 'reddit_thread'.")
            sys.exit(1)

        # Check that all three additional arguments are provided
        if not args.bg_video:
            print("Error: --bg_video is required for 'reddit_thread'.")
            sys.exit(1)

        reddit_thread = RedditThread(args.thread_link, args.bg_video, args.bg_music)
        reddit_thread.generate_short()
    else:
        print('invalid content type')

if __name__ == '__main__':
    main()