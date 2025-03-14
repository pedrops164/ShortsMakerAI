from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager
import time

# for image concatenation
from PIL import Image, ImageOps
import os

# import narration for text-to-speech
from narration import create_audio_file

# Set a character threshold for grouping paragraphs
CHARACTER_THRESHOLD = 300

class FetchingPageError(Exception):
    def __init__(self):
        self.message = "Failed to fetch the page"
        super().__init__(self.message)

class SeleniumError(Exception):
    def __init__(self, message):
        self.message = f"Selenium error: {message}"
        super().__init__(self.message)

def scrape_reddit_story(thread_url, output_file, tmp_folder='tmp', emotions={}):
    """
    Scrapes the title and content of a Reddit thread using Selenium.
    :param url: URL of the Reddit thread
    :return: Dictionary with title and content
    """
    
    service = Service(GeckoDriverManager().install())

    # Set up Firefox in headless mode
    options = webdriver.FirefoxOptions()
    options.add_argument("--width=1920")
    options.add_argument("--height=1080")
    options.add_argument("--headless")  # Run without opening a browser
    options.set_preference('intl.accept_languages', 'en-US, en')

    # Launch Firefox with Selenium
    driver = webdriver.Firefox(service=service, options=options)

    try:
        # Open the Reddit thread
        driver.get(thread_url)

        # get banner element (shows subreddit, author, date)
        banner_element = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/shreddit-app/div[2]/div/div/main/shreddit-post/div[1]"))
        )
        # get title element (shows title of post)
        title_element = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/shreddit-app/div[2]/div/div/main/shreddit-post/h1"))
        )
        title_text = title_element.get_attribute("aria-label").replace("Post Title: ", "").strip()
        
        # save header of the post as image
        save_post_header(driver, banner_element, title_element, tmp_folder)
        # save audio of title of post
        create_audio_file(title_text, f'{tmp_folder}/audio_title.mp3', emotions)

        # first we need to click read more to load all paragraphs
        read_more_button_xpath = "/html/body/shreddit-app/div[2]/div/div/main/shreddit-post/div[3]/div/button"
        read_more_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, read_more_button_xpath))
        )
        read_more_button.click()

        # Wait for the content to appear
        content_element = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/shreddit-app/div[2]/div/div/main/shreddit-post/div[3]/div/div[1]"))
        )
        
        # Extract paragraphs
        paragraphs = content_element.find_elements(By.TAG_NAME, "p")

        if not paragraphs:
            raise Exception("No paragraphs found")

        current_group = []  # Store paragraphs for the current batch
        current_text = ""
        current_text_length = 0
        screenshot_index = 1
        
        # Iterate through paragraphs and capture individual screenshots
        for i, paragraph in enumerate(paragraphs):
            paragraph_text = paragraph.text.strip()

            if not paragraph_text:  # Skip empty paragraphs
                continue

            # Add paragraph to the group
            current_group.append(paragraph)
            current_text += paragraph_text + "\n"
            current_text_length += len(paragraph_text)

            # Check if the total text length exceeds the threshold
            if current_text_length >= CHARACTER_THRESHOLD:
                # save the group of paragraphs as a screenshot
                save_screenshot_group(driver, current_group, screenshot_index, tmp_folder)
                # convert group text to audio and save
                create_audio_file(current_text.strip(), f'{tmp_folder}/audio_{screenshot_index}.mp3', emotions)
                screenshot_index += 1

                # Reset for next group
                current_group = []
                current_text = ""
                current_text_length = 0

        # **Ensure the last remaining paragraphs are saved** (if any)
        if current_group:
            # save the group of paragraphs as a screenshot
            save_screenshot_group(driver, current_group, screenshot_index, tmp_folder)
            # convert group text to audio and save
            create_audio_file(current_text.strip(), f'{tmp_folder}/audio_{screenshot_index}.mp3', emotions)
        
        content = "\n".join([p.get_attribute("textContent").strip() for p in paragraphs if p.get_attribute("textContent").strip()])

    except Exception as e:
        raise SeleniumError(str(e))

    finally:
        driver.quit()

def save_post_header(driver, banner_element, title_element, output_folder):
    """
    Saves a screenshot of the post header.
    :param driver: Selenium WebDriver instance
    :param output_folder: Folder where images will be saved
    """

    banner_temp_path = f"{output_folder}/temp_banner.png"
    # get screenshots of entire post
    banner_element.screenshot(banner_temp_path)

    title_temp_path = f"{output_folder}/temp_title.png"
    # get screenshots of entire post
    title_element.screenshot(title_temp_path)

    merged_header_image = merge_screenshots_vertically([banner_temp_path, title_temp_path])
    final_header_image_path = f"{output_folder}/header.png"
    cropped_image = crop_whitespace(merged_header_image, cut_right=15)
    cropped_image.save(final_header_image_path)

def save_screenshot_group(driver, paragraph_group, screenshot_index, output_folder):
    """
    Saves a screenshot for a grouped set of paragraphs.
    :param driver: Selenium WebDriver instance
    :param paragraph_group: List of WebElements containing paragraphs
    :param screenshot_index: Index for the saved file name
    :param output_folder: Folder where images will be saved
    """
    # Scroll into view of the first paragraph in the group
    driver.execute_script("arguments[0].scrollIntoView();", paragraph_group[0])
    time.sleep(1)  # Allow time for rendering

    # Capture screenshots of all grouped paragraphs
    screenshot_filenames = []
    for j, p in enumerate(paragraph_group):
        filename = f"{output_folder}/temp_{screenshot_index}_{j}.png"
        p.screenshot(filename)
        screenshot_filenames.append(filename)

    # Concatenate and save the final grouped screenshot
    if screenshot_filenames:
        merged_image = merge_screenshots_vertically(screenshot_filenames)
        cropped_image = crop_whitespace(merged_image)
        final_screenshot_filename = f"{output_folder}/group_{screenshot_index}.png"
        cropped_image.save(final_screenshot_filename)
        print(f"Saved grouped screenshot: {final_screenshot_filename}")

def crop_whitespace(image, cut_right=0):
    """Crops the extra white space on the right of the image."""
    if cut_right > 0:
        image = image.crop((0, 0, image.width - cut_right, image.height))
    bbox = ImageOps.invert(image).getbbox()
    trimmed_image = image.crop(bbox)
    # add white border all around for visuals
    res = ImageOps.expand(trimmed_image, border=10, fill='white')
    return res

def merge_screenshots_vertically(image_paths):
    """
    Merges multiple images vertically into a single image.
    :param image_paths: List of image file paths to merge
    :return: Merged PIL image
    """
    images = [Image.open(img) for img in image_paths]

    # Get total height and max width
    total_height = sum(img.height for img in images)
    max_width = max(img.width for img in images)

    # Create a new blank image
    merged_image = Image.new("RGB", (max_width, total_height), "white")

    # Paste images into new image
    y_offset = 0
    for img in images:
        merged_image.paste(img, (0, y_offset))
        y_offset += img.height

    # Cleanup temporary images
    for img in image_paths:
        os.remove(img)

    return merged_image