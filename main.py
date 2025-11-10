"""
FastAPI Server for ESP32 E-Paper Display
Fetches light novels from Kavita and serves as 1-bit images
"""

import io
import sys

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from contextlib import asynccontextmanager
from typing import Optional
from pathlib import Path

from utils.logger import get_logger

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.kavita.client import KavitaClient, KavitaConfig
from modules.image.processor import ColorMode, DitherMode, ImageProcessor
from models import (
    LibraryResponse,
    SeriesResponse,
    ChapterResponse,
    ImageFormat,
)
from config import settings

# Configure logging
logger = get_logger()

# Global instances
kavita_client: Optional[KavitaClient] = None
image_processor: Optional[ImageProcessor] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources"""
    global kavita_client, image_processor

    # Initialize Kavita client
    config = KavitaConfig(
        base_url=settings.kavita_base_url,
        api_key=settings.kavita_api_key,
        plugin_name=settings.kavita_plugin_name,
    )

    kavita_client = KavitaClient(config)

    # Authenticate with Kavita
    auth_success = await kavita_client.authenticate()
    if not auth_success:
        logger.error("Failed to authenticate with Kavita server")
    else:
        logger.info("Successfully authenticated with Kavita server")

    # Initialize image processor
    image_processor = ImageProcessor(
        width=settings.display_width,
        height=settings.display_height,
        font_size=settings.font_size,
        font_path=settings.font_path,
    )

    logger.info(f"Server started on {settings.server_host}:{settings.server_port}")
    logger.info(f"Display size: {settings.display_width}x{settings.display_height}")

    yield

    # Cleanup
    if kavita_client:
        await kavita_client.close()
    logger.info("Server shutdown complete")


app = FastAPI(
    title="ESP32 Kavita Reader API",
    description="Backend API for ESP32 e-paper display (400x300) to read Kavita light novels",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "ESP32 Kavita Reader API",
        "version": "1.0.0",
        "display": {"width": settings.display_width, "height": settings.display_height},
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "kavita": {
            "connected": kavita_client.token is not None,
            "base_url": settings.kavita_base_url,
        },
        "display": {
            "width": settings.display_width,
            "height": settings.display_height,
            "font_size": settings.font_size,
        },
    }


@app.get("/libraries", response_model=list[LibraryResponse])
async def get_libraries():
    """Get all available libraries from Kavita"""
    try:
        libraries = await kavita_client.get_libraries()
        return libraries
    except Exception as e:
        logger.error(f"Failed to fetch libraries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/series/{library_id}", response_model=list[SeriesResponse])
async def get_series(library_id: int):
    """Get all series in a library"""
    try:
        series = await kavita_client.get_series(library_id)
        return series
    except Exception as e:
        logger.error(f"Failed to fetch series: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chapters/{series_id}", response_model=list[ChapterResponse])
async def get_chapters(series_id: int):
    """Get all chapters for a series"""
    try:
        volumes = await kavita_client.get_volumes(series_id)
        all_chapters = []

        for volume in volumes:
            chapters = await kavita_client.get_chapters(volume["id"])
            all_chapters.extend(chapters)

        return all_chapters
    except Exception as e:
        logger.error(f"Failed to fetch chapters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chapter/text/{chapter_id}")
async def get_chapter_text(
    chapter_id: int,
    page: int = Query(default=0, ge=0, description="Page number to render"),
    format: ImageFormat = Query(default=ImageFormat.PNG, description="Output format"),
):
    """
    Get chapter text rendered as 1-bit image for 400x300 display

    Works with EPUB/PDF chapters that have text content.

    - **chapter_id**: ID of the chapter to fetch
    - **page**: Page number to render (for pagination)
    - **format**: Output format (png, raw, hex)

    Returns:
    - PNG: Image preview
    - RAW: Raw bytes for ESP32 (50 bytes per line, 300 lines = 15000 bytes)
    - HEX: JSON with hex string for debugging
    """
    try:
        # Get chapter metadata
        metadata = await kavita_client.get_chapter_metadata(chapter_id)

        # Get book resources (for text extraction)
        resources = await kavita_client.get_book_resources(chapter_id)

        if not resources or "content" not in resources:
            raise HTTPException(
                status_code=404,
                detail="Chapter text not found. This might be an image-based chapter. Try /chapter/image instead.",
            )

        # Extract text content
        content = resources.get("content", "")

        # Simple pagination: split text into chunks
        # Each page can fit ~20-25 lines depending on font size
        chars_per_page = 800  # Approximate characters per page
        total_pages = (len(content) + chars_per_page - 1) // chars_per_page

        start_idx = page * chars_per_page
        end_idx = min(start_idx + chars_per_page, len(content))

        if start_idx >= len(content):
            raise HTTPException(
                status_code=404, detail=f"Page {page} not found. Total pages: {total_pages}"
            )

        page_text = content[start_idx:end_idx]

        # Convert text to 1-bit image
        img = image_processor.text_to_1bit_image(page_text)

        # Return in requested format
        if format == ImageFormat.PNG:
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            return StreamingResponse(buf, media_type="image/png")

        elif format == ImageFormat.RAW:
            raw_bytes = image_processor.image_to_raw_bytes(img)
            return Response(
                content=raw_bytes,
                media_type="application/octet-stream",
                headers={
                    "X-Image-Width": str(img.width),
                    "X-Image-Height": str(img.height),
                    "X-Image-Size": str(len(raw_bytes)),
                    "X-Total-Pages": str(total_pages),
                    "X-Current-Page": str(page),
                },
            )

        elif format == ImageFormat.HEX:
            hex_string = image_processor.image_to_hex_string(img)
            return {
                "hex": hex_string,
                "width": img.width,
                "height": img.height,
                "total_pages": total_pages,
                "current_page": page,
            }

    except Exception as e:
        logger.error(f"Failed to process chapter: {e}", exc_info=e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chapter/info/{chapter_id}")
async def get_chapter_info(chapter_id: int):
    """Get chapter information including total pages"""
    try:
        metadata = await kavita_client.get_chapter_metadata(chapter_id)

        # Try to get text content for page count estimation
        try:
            resources = await kavita_client.get_book_resources(chapter_id)
            content = resources.get("content", "") if resources else ""
            chars_per_page = 800
            total_pages = (
                (len(content) + chars_per_page - 1) // chars_per_page
                if content
                else metadata.get("pages", 0)
            )
        except Exception as e:
            logger.warning("Error fetching book resources", exc_info=e)
            total_pages = metadata.get("pages", 0)

        return {
            "chapter_id": chapter_id,
            "total_pages": total_pages,
            "title": metadata.get("title", "Unknown"),
            "number": metadata.get("number", ""),
            "volumeId": metadata.get("volumeId"),
            "seriesId": metadata.get("seriesId"),
            "libraryId": metadata.get("libraryId"),
        }
    except Exception as e:
        logger.error(f"Failed to fetch chapter info: {e}", exc_info=e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chapter/image/{chapter_id}")
async def get_chapter_image(
    chapter_id: int,
    page: int = Query(default=0, ge=0),
    format: ImageFormat = Query(default=ImageFormat.PNG),
    color_mode: ColorMode = Query(default=ColorMode.ONE_BIT),
    dither_mode: DitherMode = Query(default=DitherMode.FLOYD_STEINBERG),
    threshold: int = Query(default=128, ge=0, le=255),
):
    """
    Get chapter images converted to display format
    Works with image-based chapters (manga, comics, scanned books).
    """
    try:
        # Get chapter metadata to know total pages
        metadata = await kavita_client.get_chapter_metadata(chapter_id)
        total_pages = metadata.get("pages", 0)
        if page >= total_pages:
            raise HTTPException(
                status_code=404, detail=f"Page {page} not found. Total pages: {total_pages}"
            )

        # Download specific page
        image_data = await kavita_client.download_chapter_page(chapter_id, page)

        # Process image with selected mode and dithering
        img = image_processor.image_to_display_format(
            image_data,
            color_mode=color_mode,
            dither_mode=dither_mode,
            threshold=threshold,
        )

        # For 4-level mode, convert to raw format for ESP32
        if color_mode == ColorMode.FOUR_LEVEL and format == ImageFormat.BMP:
            # Convert to raw 2-bit packed format
            raw_data = convert_to_4level_raw(img)

            logger.info(f"Sending raw 4-level data: {len(raw_data)} bytes")

            return Response(
                content=raw_data,
                media_type="application/octet-stream",
                headers={
                    "Content-Length": str(len(raw_data)),
                    "X-Image-Width": str(img.width),
                    "X-Image-Height": str(img.height),
                    "X-Total-Pages": str(total_pages),
                    "X-Current-Page": str(page),
                    "X-Color-Mode": "4level-raw",
                    "X-Dither-Mode": dither_mode.value,
                    "Cache-Control": "no-cache",
                },
            )

        # Return in requested format for other cases
        buf = io.BytesIO()

        if format == ImageFormat.PNG:
            img.save(buf, format="PNG", optimize=False)
            media_type = "image/png"
        elif format == ImageFormat.BMP:
            img.save(buf, format="BMP")
            media_type = "image/bmp"

        buf.seek(0)
        data = buf.getvalue()

        return Response(
            content=data,
            media_type=media_type,
            headers={
                "Content-Length": str(len(data)),
                "X-Image-Width": str(img.width),
                "X-Image-Height": str(img.height),
                "X-Total-Pages": str(total_pages),
                "X-Current-Page": str(page),
                "X-Color-Mode": color_mode.value,
                "X-Dither-Mode": dither_mode.value,
                "X-Threshold": str(threshold) if dither_mode == DitherMode.THRESHOLD else "N/A",
            },
        )
    except Exception as e:
        logger.error(f"Failed to process chapter image: {e}", exc_info=e)
        raise HTTPException(status_code=500, detail=str(e))


def convert_to_4level_raw(img) -> bytes:
    """Convert grayscale image to packed 4-level format (2 bits per pixel)"""
    width, height = img.size
    pixels = img.load()

    # Calculate buffer size (4 pixels per byte)
    buffer_size = (width * height + 3) // 4
    data = bytearray(buffer_size)

    for y in range(height):
        for x in range(width):
            gray_value = pixels[x, y]

            # Convert to 2-bit level
            if gray_value < 64:
                level = 0b00  # Black
            elif gray_value < 128:
                level = 0b01  # Dark gray
            elif gray_value < 192:
                level = 0b10  # Light gray
            else:
                level = 0b11  # White

            # Pack into buffer (4 pixels per byte, MSB first)
            pixel_index = y * width + x
            byte_index = pixel_index // 4
            bit_position = (3 - (pixel_index % 4)) * 2

            data[byte_index] |= level << bit_position

    return bytes(data)


# Additional endpoints for ESP32 convenience


@app.get("/progress/{chapter_id}")
async def get_reading_progress(chapter_id: int):
    """Get reading progress/bookmark for a chapter"""
    try:
        progress = await kavita_client.get_bookmark(chapter_id)
        return progress
    except Exception as e:
        logger.error(f"Failed to get progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/progress/{chapter_id}")
async def save_reading_progress(
    chapter_id: int,
    page: int = Query(..., ge=0),
    volume_id: int = Query(...),
    series_id: int = Query(...),
    library_id: int = Query(...),
):
    """Save reading progress for a chapter"""
    try:
        success = await kavita_client.save_progress(
            chapter_id=chapter_id,
            page_num=page,
            volume_id=volume_id,
            series_id=series_id,
            library_id=library_id,
        )
        return {"success": success, "chapter_id": chapter_id, "page": page}
    except Exception as e:
        logger.error(f"Failed to save progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mark-read/{chapter_id}")
async def mark_as_read(chapter_id: int):
    """Mark chapter as read"""
    try:
        success = await kavita_client.mark_chapter_as_read(chapter_id)
        return {"success": success, "chapter_id": chapter_id}
    except Exception as e:
        logger.error(f"Failed to mark as read: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.server_host,
        port=settings.server_port,
        log_level=settings.log_level.lower(),
    )
