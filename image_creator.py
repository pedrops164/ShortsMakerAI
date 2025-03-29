from PIL import Image, ImageDraw, ImageFont, ImageSequence, ImageColor
import os
from praw.models import Comment
from util import split_paragraphs_from_text

TMP_FOLDER = os.environ.get('TMP_FOLDER')

class RedditImageCreator:
    def __init__(self, font_path="static/fonts/Roboto-Bold.ttf", font_size=30, dark_mode=True):
        self.image_num = 0
        self.font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
        self.font_small = ImageFont.truetype(font_path, 18) if font_path else ImageFont.load_default()
        self.image_width = 576
        self.dark_mode = dark_mode
        self.font_color = (255, 255, 255) if dark_mode else (0, 0, 0)
        self.bg_color = ImageColor.getrgb("#0E1113") if dark_mode else ImageColor.getrgb("#FFFFFF")

    def create_text_image(
        self,
        text,
        save_image=False,
        line_spacing=2,              # Extra spacing between lines
        side_margin=10,               # Horizontal margin
        top_bottom_margin=8          # Vertical margin on top and bottom
    ):
        """
        Creates an image where the width is fixed, and the height grows
        to fit all wrapped text lines.
        
        :param text: The text to display in the image.
        :param output_filename: File path to save the generated image.
        :param font_path: Path to .ttf font file, or None to use a default font.
        :param font_size: Size of the font in points.
        :param line_spacing: Extra vertical space between lines of text (px).
        :param side_margin: Margin on the left and right of the text (px).
        :param top_bottom_margin: Margin at the top and bottom of the text (px).
        """
        # 1. Create a temporary image to measure text
        temp_img = Image.new("RGB", (1, 1))
        temp_draw = ImageDraw.Draw(temp_img)

        # 3. Word-wrap the text so each line fits within fixed_width - side margins
        words = text.split()
        lines = []
        current_line = ""

        max_line_width = self.image_width - 2 * side_margin

        for word in words:
            test_line = word if not current_line else f"{current_line} {word}"
            # Measure text
            left, top, right, bottom = temp_draw.textbbox((0, 0), test_line, font=self.font)
            test_line_width = right - left

            if test_line_width <= max_line_width:
                current_line = test_line
            else:
                # Add the current_line to lines, then start a new line with the current word
                lines.append(current_line)
                current_line = word

        # Don't forget the last line
        if current_line:
            lines.append(current_line)

        # 4. Calculate total text height
        line_heights = []
        for line in lines:
            left, top, right, bottom = temp_draw.textbbox((0, 0), line, font=self.font)
            line_height = bottom - top
            line_heights.append(line_height)

        # Sum all line heights + line spacing between them
        total_text_height = sum(line_heights) + line_spacing * (len(lines) - 1)

        # Final image height (with top/bottom margins)
        #final_height = total_text_height + 2 * top_bottom_margin
        final_height = total_text_height + 1 * top_bottom_margin

        # 5. Create the final image with the computed height
        img = Image.new("RGB", (self.image_width, final_height), color=self.bg_color)
        draw = ImageDraw.Draw(img)

        # 6. Draw each line
        #y_offset = top_bottom_margin
        y_offset = 0
        for line_height, line_text in zip(line_heights, lines):
            left, top, right, bottom = draw.textbbox((0, 0), line_text, font=self.font)
            text_width = right - left
            # Center the text horizontally within (max_line_width)
            x_pos = (self.image_width - text_width) // 2
            draw.text((x_pos, y_offset), line_text, font=self.font, fill=self.font_color)
            y_offset += line_height + line_spacing

        # 7. Save the final image
        if save_image:
            output_filename = self._save_image(img)
            return img, output_filename
        return img, None
    
    def _save_image(self, image):
        """
        Save the image to a file.
        """
        output_filename = f"{TMP_FOLDER}/image_{self.image_num}.png"
        self.image_num += 1
        image.save(output_filename)
        print(f"Saved text image: {output_filename}")
        return output_filename

    def _create_post_gif(
        self,
        content_image,
        output_gif_path="appended.gif"
    ):
        """
        Appends an animated GIF on top of a static image vertically,
        saving the final result as a new animated GIF.

        Top portion: frames from 'animated_gif_path'
        Bottom portion: 'content_image_path' (does NOT animate; it stays static).

        :param animated_gif_path: Path to the source animated GIF.
        :param content_image_path: Path to the static image (PNG/JPG).
        :param output_gif_path: Name/path of the resulting animated GIF.
        """
        header_gif_path = "static/animated_header_dark.gif" if self.dark_mode else "static/animated_header_white.gif"
        footer_path = "static/footer_dark.png" if self.dark_mode else "static/footer_white.png"
        # Open the animated GIF
        with Image.open(header_gif_path) as anim_gif:
            # Convert first frame just to get size
            first_frame = anim_gif.convert("RGBA")
            gif_width, gif_height = first_frame.size
            
            # Open the static (text) image and ensure RGBA
            #static_image = Image.open(content_image_path).convert("RGBA")
            static_image = content_image.convert("RGBA")
            text_width, text_height = static_image.size

            footer_image = Image.open(footer_path).convert("RGBA")
            footer_width, footer_height = footer_image.size
            
            # If widths differ, decide whether to resize one or the other
            # Here, for simplicity, we'll make both match the max of the two widths
            new_width = max(gif_width, text_width)
            
            # Optionally resize the GIF frames or the text image so widths match
            # (If you want everything to have a uniform width.)
            # For example, let's unify the width by scaling the text image:
            if text_width != new_width:
                scale_factor = new_width / text_width
                new_height = int(text_height * scale_factor)
                static_image = static_image.resize((new_width, new_height), Image.LANCZOS)
                text_width, text_height = new_width, new_height
            
            # We'll do the same for GIF frames. This means resizing each frame.
            frames = []
            for frame in ImageSequence.Iterator(anim_gif):
                frame_rgba = frame.convert("RGBA")
                if gif_width != new_width:
                    scale_factor_gif = new_width / gif_width
                    new_height_gif = int(gif_height * scale_factor_gif)
                    frame_rgba = frame_rgba.resize((new_width, new_height_gif), Image.LANCZOS)
                    current_gif_width, current_gif_height = new_width, new_height_gif
                else:
                    current_gif_width, current_gif_height = gif_width, gif_height
                
                # Create a new image for each frame: total height = gif + text
                total_height = current_gif_height + text_height + footer_height
                new_frame = Image.new("RGBA", (new_width, total_height), (255, 255, 255, 0))
                
                # Paste the GIF frame on top
                new_frame.paste(frame_rgba, (0, 0), frame_rgba)
                # Paste the text image below
                new_frame.paste(static_image, (0, current_gif_height), static_image)
                # Paste the footer image at the bottom
                #new_frame.paste(footer, (0, total_height - footer.size[1]), footer)
                new_frame.paste(footer_image, (0, current_gif_height + text_height), footer_image)
                
                frames.append(new_frame)

            # Retrieve GIF info (like duration) from the original
            duration = anim_gif.info.get('duration', 100)  # default 100ms if missing
            loop = anim_gif.info.get('loop', 0)  # 0 means infinite loop

            # Save as a new animated GIF
            frames[0].save(
                output_gif_path,
                save_all=True,
                append_images=frames[1:],
                duration=duration,
                loop=loop,
            )

        print(f"Saved appended GIF as: {output_gif_path}")

    def create_reddit_post_gif(self, text):
        """
        Create a Reddit-style post with an animated header and footer.
        """
        # 1) Create the dynamic height text image
        text_image, _ = self.create_text_image(
            text=text,
        )

        # 2) Append the existing animated GIF on top of that text image:
        output_gif_path=f"{TMP_FOLDER}/reddit_post.gif"
        self._create_post_gif(
            content_image=text_image,
            output_gif_path=output_gif_path
        )
        return output_gif_path

    def concatenate_images(self, img1, img2, orientation="vertical"):
        """
        Concatenates two images either vertically or horizontally.
        
        :param img1: The first PIL.Image.
        :param img2: The second PIL.Image.
        :param orientation: "vertical" to stack img2 below img1, 
                            "horizontal" to place img2 to the right of img1.
        :return: The concatenated image.
        """
        if orientation == "vertical":
            # Ensure the images have the same width.
            new_width = max(img1.width, img2.width)
            new_height = img1.height + img2.height
            new_img = Image.new('RGB', (new_width, new_height), color=self.bg_color)
            new_img.paste(img1, (0, 0))
            new_img.paste(img2, (0, img1.height))
        elif orientation == "horizontal":
            # Ensure the images have the same height.
            new_width = img1.width + img2.width
            new_height = max(img1.height, img2.height)
            new_img = Image.new('RGB', (new_width, new_height), color=self.bg_color)
            new_img.paste(img1, (0, 0))
            new_img.paste(img2, (img1.width, 0))
        else:
            raise ValueError("Orientation must be either 'vertical' or 'horizontal'.")
        return new_img
    
    def create_comment_header(self, comment_author_name, dark_mode=True):
        """
        Creates a header image of size 576x20 that displays the commenter's name.
        """
        width, height = 576, 20
        
        header_img = Image.new('RGB', (width, height), color=self.bg_color)
        draw = ImageDraw.Draw(header_img)
        header_text = f"u/{comment_author_name}"
        # Calculate text width and height to center it.
        left, top, right, bottom = draw.textbbox((0, 0), header_text, font=self.font_small)
        text_height = bottom - top
        left_padding = 10
        y = (height - text_height) // 2
        draw.text((left_padding, y), header_text, fill=self.font_color, font=self.font_small)
        return header_img
    
    def create_comment_text_images_pairs(self, comment: Comment):
        """
        Create images for Reddit comments.
        """
        comment_text = comment.body
        comment_author_name = comment.author.name if comment.author else "Unknown"
        comment_paragraphs = split_paragraphs_from_text(comment_text)

        comment_images = [self.create_text_image(text=p, save_image=True)[0] for p in comment_paragraphs]
        # Create the header image
        comment_header_img = self.create_comment_header(comment_author_name)
        
        # Concatenate the header image on top of the first comment image using the helper function.
        combined_img = self.concatenate_images(comment_header_img, comment_images[0], orientation="vertical")
        
        # Replace the first image with the combined image.
        comment_images[0] = combined_img

        # save images to files and get their paths
        comment_images_paths = [self._save_image(img) for img in comment_images]
        return comment_paragraphs, comment_images_paths

# Example usage
if __name__ == "__main__":
    sample_text = (
        """Here’s an interesting Reddit post. People are debating whether cats or dogs are the best pets, and the responses are hilarious! Stay tuned for more crazy online stories. Sometimes the text can get quite long and we need to ensure it wraps. With this approach, the image height grows automatically!"""
    )
    RedditImageCreator().create_reddit_post_gif(sample_text)