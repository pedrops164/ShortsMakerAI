from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.firefox import GeckoDriverManager
import time

# for image concatenation
from PIL import Image, ImageOps
import os

# Set a character threshold for grouping paragraphs
CHARACTER_THRESHOLD = 150

class FetchingPageError(Exception):
    def __init__(self):
        self.message = "Failed to fetch the page"
        super().__init__(self.message)

class SeleniumError(Exception):
    def __init__(self, message):
        self.message = f"Selenium error: {message}"
        super().__init__(self.message)

def close_google_signin(driver):
    try:
        #driver.switch_to.frame(driver.find_element(By.XPATH, "/html/body/div[3]/iframe"))
        driver.switch_to.frame(driver.find_element(By.XPATH, "//iframe[contains(@src, 'accounts.google.com/gsi/iframe')]"))
        # we need to get rid of the google signin popup
        google_signin_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//*[local-name()='svg' and @class= 'Bz112c Bz112c-r9oPif']"))
        )
        google_signin_button.click()
        # **Switch back to the main content**
        print('Clicked google signin button.')
    except TimeoutException:
        print('Google signin button not available. Skipping clicking it.')
    finally:
        driver.switch_to.default_content()

def accept_cookies(driver):
    try:
        # Wait for the shadow host element (parent of shadow DOM)
        shadow_host = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/shreddit-app/shreddit-async-loader[2]/reddit-cookie-banner"))
        )

        # Get the shadow root using JavaScript
        #shadow_root = driver.execute_script("return arguments[0].shadowRoot", shadow_host)
        shadow_root = shadow_host.shadow_root

        # Find the Accept button inside shadow root
        accept_cookies_button = WebDriverWait(driver, 10).until(
            #EC.element_to_be_clickable((By.XPATH, "/faceplate-dialog/div[2]/shreddit-interactable-element[1]/button"))
            #EC.element_to_be_clickable((By.CSS_SELECTOR, "accept-all-cookies-button > button:nth-child(1)"))
            EC.element_to_be_clickable(shadow_root.find_element(By.CSS_SELECTOR, "faceplate-dialog shreddit-interactable-element button"))            
        )

        # Click the Accept button
        accept_cookies_button.click()
        print("Cookies accepted successfully!")

    except TimeoutException:
        print("Accept cookies button not found or already dismissed.")

def click_read_more_button(driver):
    try:
        # first we need to click read more to load all paragraphs
        read_more_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "/html/body/shreddit-app/div[2]/div/div/main/shreddit-post/div[3]/div/button"))
        )
        read_more_button.click()

    except TimeoutException:
        print('Read more button not available. Skipping clicking it.')


def scrape_reddit_story(thread_url, short_creator, narrator, tmp_folder='tmp', dark_mode=False):
    """
    Scrapes the title and content of a Reddit thread using Selenium.
    :param url: URL of the Reddit thread
    :return: Dictionary with title and content
    """

    driver = _setup_driver(dark_mode)
    try:
        # Open the Reddit thread
        driver.get(thread_url)

        # Handle Google Signin popup
        close_google_signin(driver)
        # Attempt to accept cookies
        accept_cookies(driver)

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
        header_image_path = save_post_header(banner_element, title_element, tmp_folder, dark_mode=dark_mode)
        # save audio of title of post
        title_audio_path = f'{tmp_folder}/audio_title.mp3'
        narrator.create_audio_file(title_text, title_audio_path)

        # add image audio pair of header to short creator object
        short_creator.add_image_audio_pair(header_image_path, title_audio_path)
        
        # click read more button to load all paragraphs, if it exists
        click_read_more_button(driver)

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
            if current_text_length >= CHARACTER_THRESHOLD or i == len(paragraphs) - 1:
                # save the group of paragraphs as a screenshot
                image_file_path = save_screenshot_group(driver, current_group, screenshot_index, tmp_folder, dark_mode=dark_mode)
                # convert group text to audio and save
                audio_file_path = f'{tmp_folder}/audio_{screenshot_index}.mp3'
                narrator.create_audio_file(current_text.strip(), audio_file_path)
                
                # add image audio pair of paragraph group to short creator object
                short_creator.add_image_audio_pair(image_file_path, audio_file_path)

                screenshot_index += 1

                # Reset for next group
                current_group = []
                current_text = ""
                current_text_length = 0
    except Exception as e:
        raise SeleniumError(str(e))
    finally:
        driver.quit()

def _setup_driver(dark_mode):
    service = Service(GeckoDriverManager().install())

    # Set up Firefox in headless mode
    options = webdriver.FirefoxOptions()
    options.add_argument("--width=400") # smaller width for the paragraphs to be shorter in width
    options.add_argument("--height=1080")
    options.add_argument("--headless")  # Run without opening a browser
    options.set_preference('intl.accept_languages', 'en-US, en')
    if dark_mode:
        # Set the theme to dark mode
        options.set_preference("ui.systemUsesDarkTheme", 1)

    # Launch Firefox with Selenium
    driver = webdriver.Firefox(service=service, options=options)
    return driver

def save_post_header(banner_element, title_element, output_folder, dark_mode=False):
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
    cropped_image = crop_extraspace(merged_header_image, cut_right=15, dark_mode=dark_mode)
    cropped_image.save(final_header_image_path)
    return final_header_image_path

def save_screenshot_group(driver, paragraph_group, screenshot_index, output_folder, dark_mode):
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
        cropped_image = crop_extraspace(merged_image, dark_mode=dark_mode)
        final_screenshot_filename = f"{output_folder}/temp_group_{screenshot_index}.png"
        cropped_image.save(final_screenshot_filename)
        print(f"Saved grouped screenshot: {final_screenshot_filename}")
        return final_screenshot_filename
    return None

def crop_extraspace(image, cut_right=0, dark_mode=False):
    """Crops the extra white space on the right of the image."""
    if cut_right > 0:
        image = image.crop((0, 0, image.width - cut_right, image.height))
    bbox = ImageOps.invert(image).getbbox()
    trimmed_image = image.crop(bbox)
    fill_color = '#0E1113' if dark_mode else 'white'
    # add white border all around for visuals
    res = ImageOps.expand(trimmed_image, border=10, fill=fill_color)
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