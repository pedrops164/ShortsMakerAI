import re

def sanitize_filename(filename):
    # Replace invalid filename characters on most systems with '_'
    return re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', filename).strip()
