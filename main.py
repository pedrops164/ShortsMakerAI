import sys
from templates import RedditScaryStory

def main():
    content_type = sys.argv[1]
    if content_type == 'ai_pov':
        print('ai_pov')
    elif content_type == 'reddit_story':
        assert len(sys.argv) == 3, 'Usage: python main.py reddit_story <thread_link>'
        reddit_story = RedditScaryStory(sys.argv[2])
        reddit_story.generate_short()
    else:
        print('invalid content type')

if __name__ == '__main__':
    main()