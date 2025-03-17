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

TMP_FOLDER = os.environ.get('TMP_FOLDER')

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

def scrape_reddit_thread(driver, dark_mode=False, title_only=False, character_threshold=None):
    """
    Scrapes the post and answers of a Reddit thread using Selenium.
    """
    post_title_text, post_content_texts, post_header_image_path, post_content_images_paths = scrape_reddit_post(driver, dark_mode, title_only, character_threshold)

    # scrape answers
    comment_tree_element = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, "/html/body/shreddit-app/div[2]/div/div/main/div/faceplate-batch/shreddit-comment-tree"))
    )
    comments = comment_tree_element.find_elements(By.TAG_NAME, "shreddit-comment")
    for comment in comments[:5]:
        try:
            # Locate the paragraph inside the comment
            paragraph = comment.find_element(By.XPATH, ".//div[contains(@id, '-post-rtjson-content')]//p")
            print(paragraph.text)  # Print the comment text
            print()
        except Exception as e:
            print("Error extracting comment:", e)


def scrape_reddit_post(driver, dark_mode=False, title_only=False, character_threshold=None):
    """
    Scrapes the title and content of a Reddit thread using Selenium.
    :param url: URL of the Reddit thread

    If title_only is True, the print of the entire post will be returned in title_image, and content_images_paths will be empty.
    If title_only is False, the title and content prints will be returned separately in header_image_path and content_images_paths respectively.
    If character_threshold is set, the content will be grouped into paragraphs of at most that many characters. The prints of the content will also be split accordingly.
    """
    try:
        # set return variables
        title_text = None
        content_texts = []
        header_image_path = None
        content_images_paths = []
        
        title_text, header_image_path = scrape_reddit_post_header(driver, dark_mode)

        if not title_only:
            content_texts, content_images_paths = scrape_reddit_post_content(driver, dark_mode, character_threshold)

        return title_text, content_texts, header_image_path, content_images_paths
    except Exception as e:
        raise SeleniumError(str(e))

def scrape_reddit_post_header(driver, dark_mode):
    try:
        # get banner element (shows subreddit, author, date)
        banner_element = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/shreddit-app/div[2]/div/div/main/shreddit-post/div[1]"))
        )
        # get title element (shows title of post)
        title_element = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/shreddit-app/div[2]/div/div/main/shreddit-post/h1"))
        )
        title_text = title_element.get_attribute("aria-label").replace("Post Title: ", "").strip()

        banner_temp_path = f"{TMP_FOLDER}/temp_banner.png" # path to image of banner
        title_temp_path = f"{TMP_FOLDER}/temp_title.png" # path to image of title
        # save screenshot of banner
        banner_element.screenshot(banner_temp_path)
        # save screenshot of title
        title_element.screenshot(title_temp_path)

        merged_header_image = merge_screenshots_vertically([banner_temp_path, title_temp_path])
        header_image_path = f"{TMP_FOLDER}/header.png"
        cropped_image = crop_extraspace(merged_header_image, cut_right=15, dark_mode=dark_mode)
        cropped_image.save(header_image_path)
        return title_text, header_image_path
    except Exception as e:
        raise SeleniumError(str(e))

def scrape_reddit_post_content(driver, dark_mode, character_threshold):
    content_texts = []
    content_images_paths = []

    try:
        # Wait for the content to appear
        content_element = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/shreddit-app/div[2]/div/div/main/shreddit-post/div[3]/div/div[1]"))
        )
        # Extract paragraphs
        paragraphs = content_element.find_elements(By.TAG_NAME, "p")
        if not paragraphs:
            raise Exception("No paragraphs found")
        
        if len(paragraphs) > 0:
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
                if (character_threshold is not None and current_text_length >= character_threshold) or i == len(paragraphs) - 1:
                    # save the group of paragraphs as a screenshot
                    content_image_file_path = save_screenshot_group(driver, current_group, screenshot_index, dark_mode=dark_mode)
                    content_images_paths.append(content_image_file_path)
                    content_texts.append(current_text.strip())
                    screenshot_index += 1
                    # Reset for next group
                    current_group = []
                    current_text = ""
                    current_text_length = 0
        return content_texts, content_images_paths
    except Exception as e:
        raise SeleniumError(str(e))

def setup_driver_reddit(thread_url, dark_mode):
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
    # Open the Reddit thread
    try:
        driver.get(thread_url)
        # Handle Google Signin popup
        close_google_signin(driver)
        # Attempt to accept cookies
        accept_cookies(driver)
        # click read more button to load all paragraphs, if it exists
        click_read_more_button(driver)
        return driver
    except Exception as e:
        raise SeleniumError(str(e))

def save_screenshot_group(driver, paragraph_group, screenshot_index, dark_mode):
    """
    Saves a screenshot for a grouped set of paragraphs.
    :param driver: Selenium WebDriver instance
    :param paragraph_group: List of WebElements containing paragraphs
    :param screenshot_index: Index for the saved file name
    :param dark_mode: Whether to use dark mode"""
    # Scroll into view of the first paragraph in the group
    driver.execute_script("arguments[0].scrollIntoView();", paragraph_group[0])
    time.sleep(1)  # Allow time for rendering

    # Capture screenshots of all grouped paragraphs
    screenshot_filenames = []
    for j, p in enumerate(paragraph_group):
        filename = f"{TMP_FOLDER}/temp_{screenshot_index}_{j}.png"
        p.screenshot(filename)
        screenshot_filenames.append(filename)

    # Concatenate and save the final grouped screenshot
    if screenshot_filenames:
        merged_image = merge_screenshots_vertically(screenshot_filenames)
        cropped_image = crop_extraspace(merged_image, dark_mode=dark_mode)
        final_screenshot_filename = f"{TMP_FOLDER}/temp_group_{screenshot_index}.png"
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

if __name__ == '__main__':
    # test scrape_reddit_thread:
    thread_url = "https://www.reddit.com/r/scarystories/comments/ijjshz/run/"  # Scary story thread
    driver = setup_driver_reddit(thread_url, dark_mode=True)
    scrape_reddit_thread(driver, dark_mode=True)