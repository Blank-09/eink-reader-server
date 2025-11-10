"""
Image Processor Module (modules/image/processor.py)
Converts text and images to 1-bit format for ESP32 e-paper displays (400x300)
"""

from enum import Enum
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import io
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ColorMode(Enum):
    ONE_BIT = "1bit"  # Black and white only
    FOUR_LEVEL = "4level"  # Black, dark gray, light gray, white


class DitherMode(str, Enum):
    FLOYD_STEINBERG = "floyd_steinberg"
    THRESHOLD = "threshold"
    NONE = "none"


class ImageProcessor:
    def __init__(
        self,
        width: int = 400,
        height: int = 300,
        font_path: Optional[str] = None,
        font_size: int = 20,
    ):
        self.width = width
        self.height = height
        self.font_size = font_size

        # Try to load font, fallback to default
        try:
            if font_path:
                self.font = ImageFont.truetype(font_path, font_size)
            else:
                self.font = ImageFont.load_default()
        except Exception as e:
            logger.warning(f"Failed to load font: {e}, using default")
            self.font = ImageFont.load_default()

    def text_to_1bit_image(
        self, text: str, padding: int = 10, line_spacing: int = 5
    ) -> Image.Image:
        """Convert text to 1-bit image suitable for e-paper display"""
        # Create a white image
        img = Image.new("1", (self.width, self.height), 1)
        draw = ImageDraw.Draw(img)

        # Word wrap the text
        lines = self._wrap_text(text, self.width - (2 * padding))

        y = padding
        for line in lines:
            if y + self.font_size > self.height - padding:
                break  # Stop if we exceed height

            draw.text((padding, y), line, font=self.font, fill=0)
            y += self.font_size + line_spacing

        return img

    def image_to_1bit(
        self,
        image_data: bytes,
        auto_rotate: bool = True,
        dither_mode: DitherMode = DitherMode.FLOYD_STEINBERG,
        threshold: int = 128,
    ) -> Image.Image:
        """
        Convert image to 1-bit format with optional auto-rotation and configurable dithering

        Args:
            image_data: Raw image bytes
            auto_rotate: Automatically rotate portrait images to landscape
            dither_mode: Dithering algorithm to use (floyd_steinberg, threshold, none)
            threshold: Threshold value for threshold mode (0-255, default 128)
        """
        try:
            img = Image.open(io.BytesIO(image_data))

            # Auto-rotate portrait images to landscape if needed
            if auto_rotate:
                img_width, img_height = img.size
                display_is_landscape = self.width > self.height
                image_is_portrait = img_height > img_width

                # If display is landscape but image is portrait, rotate 90 degrees
                if display_is_landscape and image_is_portrait:
                    # Rotate counter-clockwise (90 degrees) to make it landscape
                    img = img.rotate(90, expand=True)
                    logger.info(f"Rotated portrait image {img_width}x{img_height} to landscape")

            # Resize to fit display while maintaining aspect ratio
            img.thumbnail((self.width, self.height), Image.Resampling.LANCZOS)

            # Convert to grayscale first
            img = img.convert("L")

            # Apply selected dithering/threshold method
            if dither_mode == DitherMode.FLOYD_STEINBERG:
                img = img.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
            elif dither_mode == DitherMode.THRESHOLD:
                # Manual threshold conversion
                img = img.point(lambda x: 255 if x > threshold else 0, mode="1")
            elif dither_mode == DitherMode.NONE:
                img = img.convert("1", dither=Image.Dither.NONE)

            # Center the image on a white background
            centered = Image.new("1", (self.width, self.height), 1)
            x = (self.width - img.width) // 2
            y = (self.height - img.height) // 2
            centered.paste(img, (x, y))

            return centered
        except Exception as e:
            logger.error(f"Failed to process image: {e}")
            raise

    def image_to_display_format(
        self,
        image_data: bytes,
        auto_rotate: bool = True,
        color_mode: ColorMode = ColorMode.ONE_BIT,
        dither_mode: DitherMode = DitherMode.FLOYD_STEINBERG,
        threshold: int = 128,
    ) -> Image.Image:
        """
        Convert image to display format with optional auto-rotation and configurable dithering

        Args:
            image_data: Raw image bytes
            auto_rotate: Automatically rotate portrait images to landscape
            color_mode: Color depth mode (1bit or 4level grayscale)
            dither_mode: Dithering algorithm to use (floyd_steinberg, threshold, none)
            threshold: Threshold value for threshold mode (0-255, default 128)
        """
        try:
            img = Image.open(io.BytesIO(image_data))

            # Auto-rotate portrait images to landscape if needed
            if auto_rotate:
                img_width, img_height = img.size
                display_is_landscape = self.width > self.height
                image_is_portrait = img_height > img_width

                # If display is landscape but image is portrait, rotate 90 degrees
                if display_is_landscape and image_is_portrait:
                    # Rotate counter-clockwise (90 degrees) to make it landscape
                    img = img.rotate(90, expand=True)
                    logger.info(f"Rotated portrait image {img_width}x{img_height} to landscape")

            # Resize to fit display while maintaining aspect ratio
            img.thumbnail((self.width, self.height), Image.Resampling.LANCZOS)

            # Convert to grayscale first
            img = img.convert("L")

            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.5)  # 1.5x contrast

            # Increase sharpness (crisper text)
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(2.0)  # 2x sharpness

            # Slightly increase brightness (prevents muddy grays)
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(1.1)

            # Apply color mode conversion
            if color_mode == ColorMode.ONE_BIT:
                # Original 1-bit conversion
                if dither_mode == DitherMode.FLOYD_STEINBERG:
                    img = img.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
                elif dither_mode == DitherMode.THRESHOLD:
                    img = img.point(lambda x: 255 if x > threshold else 0, mode="1")
                elif dither_mode == DitherMode.NONE:
                    img = img.convert("1", dither=Image.Dither.NONE)

                # Center on white background
                centered = Image.new("1", (self.width, self.height), 1)

            elif color_mode == ColorMode.FOUR_LEVEL:
                # 4-level grayscale: 0 (black), 85 (dark gray), 170 (light gray), 255 (white)
                if dither_mode == DitherMode.FLOYD_STEINBERG:
                    # Floyd-Steinberg dithering for 4 levels
                    img = self._dither_4level_floyd_steinberg(img)
                elif dither_mode == DitherMode.THRESHOLD:
                    # Multi-threshold conversion
                    img = self._convert_4level_threshold(img)
                elif dither_mode == DitherMode.NONE:
                    # Simple quantization to 4 levels
                    img = img.point(lambda x: self._quantize_4level(x))

                # Center on white background
                centered = Image.new("L", (self.width, self.height), 255)

            x = (self.width - img.width) // 2
            y = (self.height - img.height) // 2
            centered.paste(img, (x, y))

            return centered

        except Exception as e:
            logger.error(f"Failed to process image: {e}")
            raise

    def _quantize_4level(self, value: int) -> int:
        """Quantize grayscale value to 4 levels"""
        if value < 64:
            return 0  # Black
        elif value < 128:
            return 85  # Dark gray
        elif value < 192:
            return 170  # Light gray
        else:
            return 255  # White

    def _convert_4level_threshold(self, img: Image.Image) -> Image.Image:
        """Convert to 4-level grayscale using threshold method"""
        return img.point(self._quantize_4level)

    def _dither_4level_floyd_steinberg(self, img: Image.Image) -> Image.Image:
        """Apply Floyd-Steinberg dithering for 4-level grayscale"""
        pixels = img.load()
        width, height = img.size

        # Create a copy to work with
        result = img.copy()
        result_pixels = result.load()

        for y in range(height):
            for x in range(width):
                old_pixel = result_pixels[x, y]
                new_pixel = self._quantize_4level(old_pixel)
                result_pixels[x, y] = new_pixel

                error = old_pixel - new_pixel

                # Distribute error to neighboring pixels
                if x + 1 < width:
                    result_pixels[x + 1, y] = min(
                        255, max(0, result_pixels[x + 1, y] + error * 7 // 16)
                    )
                if x - 1 >= 0 and y + 1 < height:
                    result_pixels[x - 1, y + 1] = min(
                        255, max(0, result_pixels[x - 1, y + 1] + error * 3 // 16)
                    )
                if y + 1 < height:
                    result_pixels[x, y + 1] = min(
                        255, max(0, result_pixels[x, y + 1] + error * 5 // 16)
                    )
                if x + 1 < width and y + 1 < height:
                    result_pixels[x + 1, y + 1] = min(
                        255, max(0, result_pixels[x + 1, y + 1] + error * 1 // 16)
                    )

        return result

    def _wrap_text(self, text: str, max_width: int) -> list:
        """Wrap text to fit within max_width"""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            # Check if adding this word exceeds width
            test_line = " ".join(current_line + [word])
            bbox = self.font.getbbox(test_line)
            width = bbox[2] - bbox[0]

            if width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]

        if current_line:
            lines.append(" ".join(current_line))

        return lines

    def image_to_bytes(self, img: Image.Image, format: str = "PNG") -> bytes:
        """Convert PIL Image to bytes"""
        buf = io.BytesIO()
        img.save(buf, format=format)
        return buf.getvalue()

    def image_to_raw_bytes(self, img: Image.Image) -> bytes:
        """Convert 1-bit image to raw bytes for ESP32"""
        # Convert to bytes array (1 bit per pixel, packed)
        return img.tobytes()

    def image_to_hex_string(self, img: Image.Image) -> str:
        """Convert 1-bit image to hex string for ESP32"""
        raw_bytes = self.image_to_raw_bytes(img)
        return raw_bytes.hex()
