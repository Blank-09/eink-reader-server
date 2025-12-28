from PIL import Image, ImageDraw, ImageFont
import io


class Renderer:
    def __init__(self):
        self.NATIVE_WIDTH = 400
        self.NATIVE_HEIGHT = 300

        # 1. Create a 4-color palette image for quantization
        # We need exactly 768 values (256 colors * 3 RGB channels)
        self.palette_img = Image.new("P", (1, 1))

        # Define 4 gray levels
        palette_data = [
            0,
            0,
            0,  # Index 0: Black
            85,
            85,
            85,  # Index 1: Dark Gray
            170,
            170,
            170,  # Index 2: Light Gray
            255,
            255,
            255,  # Index 3: White
        ]

        # Pad with zeros to reach exactly 768 integers
        palette_data += [0] * (768 - len(palette_data))

        self.palette_img.putpalette(palette_data)

        try:
            self.font = ImageFont.truetype("arial.ttf", 14)
            self.header_font = ImageFont.truetype("arial.ttf", 16)
        except:
            self.font = ImageFont.load_default()
            self.header_font = ImageFont.load_default()

    def _pack_2bit(self, img: Image.Image) -> bytes:
        """Packs a 4-color indexed image (mode P) into raw 2-bit bytes."""
        pixels = list(img.getdata())
        packed_data = bytearray(len(pixels) // 4)

        for i in range(0, len(pixels), 4):
            # SAFTEY FIX: Use bitwise AND 3 (& 3)
            # If Pillow picks Index 4 (Black) instead of Index 0 (Black),
            # this forces it back to 0 (00), preventing byte overflow.
            p0 = pixels[i] & 3
            p1 = pixels[i + 1] & 3
            p2 = pixels[i + 2] & 3
            p3 = pixels[i + 3] & 3

            # Pack: [P0 P1 P2 P3]
            byte_val = (p0 << 6) | (p1 << 4) | (p2 << 2) | p3
            packed_data[i // 4] = byte_val

        return bytes(packed_data)

    def render_list_view(self, title: str, items: list, cursor_index: int) -> bytes:
        # 1. Create Canvas (RGB)
        img = Image.new("RGB", (400, 300), (255, 255, 255))
        draw = ImageDraw.Draw(img)

        # --- DIMENSIONS ---
        header_height = 30
        row_height = 28
        start_y = 35
        side_margin = 0
        max_visible_items = 9  # Items per page

        # Calculate Scrolling Window
        # This determines which slice of the list to show
        total_items = len(items)

        # Simple Logic: Keep cursor somewhat centered or page by page
        # Here we just calculate the 'start_index' (top item visible)
        if total_items <= max_visible_items:
            start_index = 0
        else:
            # Try to keep cursor in the middle
            half_window = max_visible_items // 2
            start_index = cursor_index - half_window

            # Clamp bounds
            if start_index < 0:
                start_index = 0
            if start_index + max_visible_items > total_items:
                start_index = total_items - max_visible_items

        # 2. Draw Header
        draw.rectangle((0, 0, 400, header_height), fill=(0, 0, 0))
        draw.text((15, 6), title, font=self.header_font, fill=(255, 255, 255))

        # Draw Counter (e.g., "5/24") in the header right side
        count_text = f"{cursor_index + 1}/{total_items}"
        # Calculate text width to align right (approximate width calc)
        text_w = len(count_text) * 8
        draw.text((390 - text_w, 8), count_text, font=self.font, fill=(255, 255, 255))

        # 3. Draw Visible Items
        box_left = side_margin
        box_right = 400 - side_margin
        text_x = side_margin + 10

        for i in range(max_visible_items):
            item_idx = start_index + i
            if item_idx >= total_items:
                break

            item = items[item_idx]
            y = start_y + (i * row_height)

            # Vertical alignment adjustment
            text_y_offset = 5

            if item_idx == cursor_index:
                # Selection Box
                draw.rectangle((box_left, y, box_right, y + row_height - 2), fill=(85, 85, 85))
                draw.text(
                    (text_x, y + text_y_offset), f"> {item}", font=self.font, fill=(255, 255, 255)
                )
            else:
                # Normal Text
                draw.text((text_x, y + text_y_offset), item, font=self.font, fill=(0, 0, 0))
                # Separator
                line_y = y + row_height - 1
                draw.line((box_left + 5, line_y, box_right - 5, line_y), fill=(170, 170, 170))

        # 4. Draw Scrollbar (Right Edge)
        if total_items > max_visible_items:
            # Dimensions of the scroll track
            track_x = 394
            track_y_start = header_height
            track_y_end = 300
            track_height = track_y_end - track_y_start

            # Draw Track Line
            draw.line((track_x + 2, track_y_start, track_x + 2, track_y_end), fill=(170, 170, 170))

            # Calculate Thumb Size & Position
            # Thumb height is proportional to visible percentage
            thumb_height = max(20, int((max_visible_items / total_items) * track_height))

            # Thumb position is proportional to start_index (how far we scrolled)
            scrollable_height = track_height - thumb_height
            max_scroll_idx = total_items - max_visible_items

            if max_scroll_idx > 0:
                thumb_y = track_y_start + int((start_index / max_scroll_idx) * scrollable_height)
            else:
                thumb_y = track_y_start

            # Draw Thumb (Black Bar)
            draw.rectangle((track_x, thumb_y, track_x + 4, thumb_y + thumb_height), fill=(0, 0, 0))

        # 5. Quantize & Pack
        final_img = img.quantize(palette=self.palette_img, dither=Image.Dither.NONE)
        return self._pack_2bit(final_img)

    def render_page(self, page_num: int, content: str, orientation: int, dither_mode: str) -> bytes:
        # 1. Setup Canvas
        if orientation == 1:
            w, h = self.NATIVE_HEIGHT, self.NATIVE_WIDTH
        else:
            w, h = self.NATIVE_WIDTH, self.NATIVE_HEIGHT

        # Draw in RGB to allow for smooth gradients if needed later
        img = Image.new("RGB", (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(img)

        # Draw Content
        draw.rectangle((0, 0, w, 40), fill=(200, 200, 200))  # Light Gray Header
        draw.text((10, 5), f"Page {page_num}", font=self.font, fill=(0, 0, 0))
        draw.text((10, 60), content, font=self.font, fill=(0, 0, 0))

        # Rotate if Portrait
        if orientation == 1:
            img = img.rotate(90, expand=True)

        # 4. Conditional Dithering
        # - FLOYD: Adds noise to smooth out gradients (Good for images/manga)
        # - NONE: Snaps to nearest color (Good for text)
        if dither_mode == "FLOYD":
            final_img = img.quantize(palette=self.palette_img, dither=Image.Dither.FLOYDSTEINBERG)
        else:
            final_img = img.quantize(palette=self.palette_img, dither=Image.Dither.NONE)

        return self._pack_2bit(final_img)

    def process_external_image(self, img: Image.Image, dither_mode: str, orientation: int) -> bytes:
        """
        Takes an RGB Image, rotates it if needed, quantizes it, and packs it.
        """
        # 1. Rotate if Portrait
        if orientation == 1:
            # Input: 300x400 -> Output: 400x300
            img = img.rotate(90, expand=True)

        # 2. Ensure RGB
        if img.mode != "RGB":
            img = img.convert("RGB")

        # 3. Apply Dithering
        if dither_mode == "FLOYD":
            final_img = img.quantize(palette=self.palette_img, dither=Image.Dither.FLOYDSTEINBERG)
        else:
            final_img = img.quantize(palette=self.palette_img, dither=Image.Dither.NONE)

        return self._pack_2bit(final_img)
