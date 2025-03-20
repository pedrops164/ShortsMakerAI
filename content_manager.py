import praw
import os
import json

_PERSIST_FILE = 'processed_links.json'

class ContentManager:
    """
    A singleton class for managing Reddit content fetching (via PRAW)
    and persistent storage of processed links (in a JSON file).
    """

    __instance = None  # class-level private instance reference

    def __new__(cls, *args, **kwargs):
        """Override __new__ to ensure only one instance is created."""
        if cls.__instance is None:
            cls.__instance = super(ContentManager, cls).__new__(cls)
        return cls.__instance

    def __init__(self):
        """
        We only want to initialize once, so we can guard with a flag or
        rely on the fact that the same instance is returned each time.
        """
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._processed_links = set()
            self.load_processed_links()

    @classmethod
    def get_instance(cls):
        """
        Optional convenience method to retrieve the singleton instance.
        """
        if cls.__instance is None:
            cls.__instance = ContentManager()
        return cls.__instance

    def load_processed_links(self):
        """
        Load previously processed links from JSON. Store them in a set
        for fast lookups.
        """
        if os.path.exists(_PERSIST_FILE):
            with open(_PERSIST_FILE, 'r') as f:
                data = json.load(f)
            self._processed_links = set(data)
        else:
            self._processed_links = set()

    def save_processed_links(self):
        """
        Save the set of processed links to a JSON file.
        """
        with open(_PERSIST_FILE, 'w') as f:
            json.dump(list(self._processed_links), f)

    def get_top_threads_link(self, subreddit_name, topn=10, time_filter='day'):
        """
        Fetch the top threads from a given subreddit. 
        Default to top 10 of 'day'.
        """
        client_id = os.getenv('REDDIT_CLIENT_ID')
        client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent='USER_AGENT'
        )

        subreddit = reddit.subreddit(subreddit_name)
        top_threads = subreddit.top(limit=topn, time_filter=time_filter)
        return [thread.url for thread in top_threads]

    def has_processed(self, link):
        """Check if we've already processed this link."""
        return link in self._processed_links

    def mark_processed(self, link):
        """Mark a link as processed and save immediately."""
        self._processed_links.add(link)
        self.save_processed_links()


# Example usage:
if __name__ == '__main__':
    # Get the singleton instance
    manager = ContentManager.get_instance()

    print('Getting top threads from Reddit...')
    top_threads_link = manager.get_top_threads_link('askreddit', 5)
    print(top_threads_link)
    print(len(top_threads_link), 'top threads retrieved.')

    # Process each link if not already processed
    for link in top_threads_link:
        if manager.has_processed(link):
            print(f'Skipping (already processed): {link}')
        else:
            print(f'Processing: {link}')
            # perform some action here
            manager.mark_processed(link)
