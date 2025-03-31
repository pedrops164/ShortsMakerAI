import re

def sanitize_filename(filename, max_length=100):
    print(f"Sanitizing filename: {filename}")
    # Replace invalid filename characters on most systems with '_'
    sanitized_base = re.sub(r'[<>:"/\\|?*\x00-\x1F.,]', '_', filename).strip()
    # Truncate the base name if it's too long.
    if len(sanitized_base) > max_length:
        sanitized_base = sanitized_base[:max_length]
    return sanitized_base

def split_paragraphs_from_text(text, character_threshold=300):
    """
    Split 'text' into chunks (paragraphs), each no more than 'character_threshold' characters long.
    Splits at every period ('.'), then accumulates sentences until adding another would exceed the threshold.
    """

    # First, split on "." to get individual sentences/phrases
    # (strip to remove leading/trailing whitespace)
    phrases = [phrase.strip() for phrase in text.split('.') if phrase.strip()]

    split_paragraphs = []
    current_paragraph = ""

    for phrase in phrases:
        # We'll re-add the period (".") and a space after each phrase
        # so that the final text looks like sentences.
        # e.g. "This is sentence one." -> "This is sentence one. "
        to_add = phrase + ". "

        # Check if adding this sentence to our current paragraph
        # would exceed the character threshold.
        if len(current_paragraph) + len(to_add) <= character_threshold:
            current_paragraph += to_add
        else:
            # If current_paragraph isn't empty, store it
            if current_paragraph.strip():
                split_paragraphs.append(current_paragraph.strip())
            # Start a new paragraph
            current_paragraph = to_add

    # After the loop, if there's anything left in current_paragraph, append it
    if current_paragraph.strip():
        split_paragraphs.append(current_paragraph.strip())

    return split_paragraphs

def replace_acronyms(title):
    title = title.replace('AITAH', 'Am I The Asshole')
    title = title.replace('AITA', 'Am I The Asshole')
    title = title.replace('WIBTA', 'Would I be the asshole')
    title = title.replace('TIFU', 'Today I Fucked Up')
    title = title.replace('TLDR', 'Too Long Didn\'t Read')
    title = title.replace('YTA', 'You\'re The Asshole')
    title = title.replace('NTA', 'Not The Asshole')
    title = title.replace('ESH', 'Everyone Sucks Here')
    title = title.replace('NAH', 'No Assholes Here')
    title = title.replace('INFO', 'Information')
    return title