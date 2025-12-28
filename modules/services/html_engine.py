from playwright.async_api import async_playwright
from PIL import Image
import io
import asyncio


class HTMLEngine:
    def __init__(self):
        self.browser = None
        self.context = None
        self.width = 400
        self.height = 300
        self.cache = {}  # {chapter_id: [bytes, bytes, ...]}
        self.current_chapter_id = None

    async def start(self):
        """Starts the browser. Call this on server startup."""
        if not self.browser:
            p = await async_playwright().start()
            # Launch headless chromium
            self.browser = await p.chromium.launch(headless=True)
            # Create a context with our specific screen size
            self.context = await self.browser.new_context(
                viewport={"width": self.width, "height": self.height}, device_scale_factor=1
            )
            print("🚀 Playwright Engine Started")

    async def render_chapter(self, chapter_id, html_content, renderer):
        """
        Loads HTML, scrolls through it, and captures 2-bit images.
        """
        if self.current_chapter_id == chapter_id and chapter_id in self.cache:
            return len(self.cache[chapter_id])

        if not self.browser:
            await self.start()

        page = await self.context.new_page()

        # 1. Load Content
        # We wrap the content in a minimal structure to apply base styles
        full_html = f"""
        <!DOCTYPE html>
        <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{ 
                        font-family: Arial, sans-serif; 
                        font-size: 24px; /* Large font for E-Ink readability */
                        margin: 10px;    /* Small margin */
                        background-color: white;
                        color: black;
                        line-height: 1.4;
                    }}
                    img {{ max-width: 100%; height: auto; }} /* Fit images */
                    p {{ margin-bottom: 1em; }}
                </style>
            </head>
            <body>{html_content}</body>
        </html>
        """

        await page.set_content(full_html)

        # 2. Calculate Layout
        # Wait for any images to load
        await page.wait_for_load_state("networkidle")

        # Get total scrollable height
        total_height = await page.evaluate("document.body.scrollHeight")

        print(f"📖 Rendering Chapter {chapter_id}: Height {total_height}px")

        # 3. Generate Slices (Pages)
        generated_pages = []

        # Loop through the content in 300px chunks
        for y in range(0, total_height, self.height):
            # Take screenshot of the specific region
            # clip: {x, y, width, height}
            # Note: We clamp height if we are at the very bottom
            clip_height = min(self.height, total_height - y)

            png_bytes = await page.screenshot(
                clip={"x": 0, "y": y, "width": self.width, "height": clip_height}
            )

            # 4. Post-Process (Convert PNG -> E-Ink 2-bit)
            # We use Pillow to load the screenshot bytes
            img = Image.open(io.BytesIO(png_bytes))

            # Handle partial last page (pad with white if < 300px)
            if clip_height < self.height:
                new_img = Image.new("RGB", (self.width, self.height), (255, 255, 255))
                new_img.paste(img, (0, 0))
                img = new_img

            # Use Renderer to Dither & Pack
            # We assume we want "FLOYD" dithering for HTML (handles images better)
            # Or "THRESHOLD" for pure text.
            # Ideally, pass this pref from DB. using FLOYD for generic HTML is safer.
            packed = renderer.process_external_image(img, "FLOYD")
            generated_pages.append(packed)

        await page.close()

        # 5. Cache
        self.cache = {chapter_id: generated_pages}
        self.current_chapter_id = chapter_id

        return len(generated_pages)

    def get_page_image(self, chapter_id, page_index):
        if chapter_id in self.cache:
            pages = self.cache[chapter_id]
            if 0 <= page_index < len(pages):
                return pages[page_index]
        return None

    async def render_scroll_view(
        self, html_content, scroll_step, renderer, orientation, dither_mode
    ):
        """
        Renders the view with dynamic viewport based on orientation.
        """
        if not self.browser:
            await self.start()

        page = await self.context.new_page()

        # 1. SET DYNAMIC VIEWPORT
        if orientation == 1:  # Portrait
            view_w, view_h = 300, 400
        else:  # Landscape
            view_w, view_h = 400, 300

        await page.set_viewport_size({"width": view_w, "height": view_h})

        # 2. Inject CSS
        full_html = f"""
        <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{ 
                        font-family: Arial; 
                        font-size: 14px; 
                        margin: 0; 
                        padding: 10px; 
                        box-sizing: border-box; /* Ensures padding is inside the width */
                        background: white; 
                        width: {view_w}px;      /* Force exact width */
                        overflow-y: hidden;     /* Hide scrollbars visually */
                    }}
                    img {{ max-width: 100%; height: auto; }}
                </style>
            </head>
            <body>{html_content}</body>
        </html>
        """
        await page.set_content(full_html)
        await page.wait_for_load_state("networkidle")

        # 3. Check Bounds (Using dynamic view_h)
        total_height = int(await page.evaluate("document.body.scrollHeight"))
        current_y = scroll_step * view_h

        # If we are strictly past the content, go to next page
        if current_y >= total_height and scroll_step > 0:
            await page.close()
            return "NEXT"

        if scroll_step == -1:
            import math

            max_steps = max(0, math.ceil(total_height / view_h) - 1)
            await page.close()
            return max_steps

        # 4. Screenshot
        await page.evaluate(f"window.scrollTo(0, {max(current_y - 40, 0)})")

        try:
            png_bytes = await page.screenshot()
        except Exception as e:
            print(f"⚠️ Boundary Error (Skipping to Next): {e}")
            await page.close()
            return "NEXT"

        await page.close()

        # 5. Process
        img = Image.open(io.BytesIO(png_bytes))

        # Pass orientation to renderer so it knows to rotate
        return renderer.process_external_image(img, dither_mode, orientation)


# Global Instance
html_engine = HTMLEngine()
