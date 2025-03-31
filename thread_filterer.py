import praw
import os
from openai import OpenAI

def select_top_threads_via_llm(posts, topn, subreddit_name):
    """
    Given a list of PRAW Submission objects, ask the LLM to pick the top 'topn' posts 
    that are most likely to drive engagement on TikTok based on their titles.
    
    The LLM should return a comma-separated list of indices corresponding to the posts.
    """
    # Create a numbered list of titles
    titles_list = [f"{idx+1}. {post.title}" for idx, post in enumerate(posts)]
    titles_str = "\n".join(titles_list)
    
    # Compose the prompt for the LLM
    prompt = f"""
You are an assistant that selects the most engaging Reddit threads for TikTok content.
Below is a list of Reddit thread titles from the subreddit '{subreddit_name}' (from the past day).
Please choose the top {topn} threads that are most likely to drive user engagement on TikTok,
focusing on those that are interesting, exciting, or controversial.
Respond with a comma-separated list of the numbers corresponding to your selections (e.g., "1, 3, 5").
List of posts:
{titles_str}
"""
    client = OpenAI(
        api_key=os.environ.get("OPENAI_KEY"),
    )
    
    # Call the OpenAI ChatCompletion API
    response = client.responses.create(
        model="gpt-4o",
        input=prompt,
        instructions="Select the most engaging threads",
        temperature=0.5,
    )
    
    answer = response.output_text
    
    # Attempt to parse the response into indices
    indices = []
    try:
        # Expecting a response like: "1, 3, 5"
        indices = [int(s.strip()) for s in answer.split(',') if s.strip().isdigit()]
    except Exception as e:
        print("Error parsing LLM response:", e)
    
    # Convert indices to zero-based and select the corresponding posts
    selected_posts = []
    for idx in indices:
        if 1 <= idx <= len(posts):
            selected_posts.append(posts[idx-1])
    return selected_posts

def get_best_subreddit_titles(topn, search_topn, subreddit_name, time_filter='day'):
    """
    Fetch the top posts from a specified subreddit, and use an LLM to get the most exciting ones"
    """
    # Initialize the Reddit instance with your developer credentials
    reddit = praw.Reddit(
        client_id=os.getenv('REDDIT_CLIENT_ID'),          # Replace with your client ID
        client_secret=os.getenv('REDDIT_CLIENT_SECRET'),  # Replace with your client secret
        user_agent='USER_AGENT'         # Replace with your user agent
    )

    # Select the AskReddit subreddit
    subreddit = reddit.subreddit(subreddit_name)
    # Retrieve the top posts from the past day, limited to 50 posts
    posts = list(subreddit.top(time_filter=time_filter, limit=search_topn))
    posts = [thread for thread in posts if not thread.over_18]
    
    # Optionally print all retrieved post titles
    print("Retrieved posts:")
    for idx, post in enumerate(posts, 1):
        print(f"{idx}. {post.title}")
    
    # Use the LLM to select the top posts based on engagement criteria
    best_posts = select_top_threads_via_llm(posts, topn, subreddit_name)
    return best_posts
    
if __name__ == "__main__":
    # Specify how many top posts to retrieve
    topn = 10  
    best_posts = get_best_subreddit_titles(topn, topn*5, 'AskReddit')
    
    print("\nSelected Top Threads:")
    for idx, post in enumerate(best_posts, 1):
        print(f"{idx}. {post.title}")