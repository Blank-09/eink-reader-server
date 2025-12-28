import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import settings
from utils.logger import configure_root_logger, get_logger
from modules.services.html_engine import html_engine

import modules.services.database as db
from modules.services.renderer import Renderer
from modules.services.workflow import WorkflowManager

from modules.api.routes import books, library
from modules.kavita.client import kavita_client, connect_kavita_server

# Setup logging
logger = get_logger()

# Global instances
# image_processor: Optional[ImageProcessor] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources"""
    global kavita_client

    configure_root_logger(logging.DEBUG)

    logger.info("Starting E-Reader OS API server...")
    db.init_db()

    await connect_kavita_server()
    await html_engine.start()

    # Initialize image processor
    # image_processor = ImageProcessor(
    #     width=settings.display_width,
    #     height=settings.display_height,
    #     font_size=settings.font_size,
    #     font_path=settings.font_path,
    # )

    logger.info(f"Server started on {settings.server_host}:{settings.server_port}")
    logger.info(f"Display size: {settings.display_width}x{settings.display_height}")

    yield

    # Cleanup
    if kavita_client:
        await kavita_client.close()

    logger.info("Server shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="E-Reader OS API",
    description="API server for ESP32-based e-reader devices",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(library.router)
app.include_router(books.router)
# app.include_router(devices.router)
# app.include_router(reading.router)
# app.include_router(input.router)
# app.include_router(button_config.router)


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "E-Reader OS API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
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


workflow = WorkflowManager()


class ButtonEvent(BaseModel):
    button: str  # Expected values: "A", "B", "C", "D", "E", "F"
    type: str  # Expected values: "single", "hold"


@app.post("/api/button")
async def receive_button_event(event: ButtonEvent):
    """
    Receives input from ESP32 and delegates it to the Workflow Manager.
    """
    print(f"🔔 Input: {event.button} ({event.type})")

    # CRITICAL CHANGE: Logic is now delegated
    # The API doesn't know about "Libraries" or "Pages".
    # It just tells the Manager: "User pressed A".
    await workflow.handle_input(event.button, event.type)

    # We return "ok" so ESP32 knows the command was received.
    # The ESP32 will immediately follow up with a GET /api/current request.
    return {"status": "ok"}


renderer = Renderer()


@app.get("/api/current")
async def get_current_view():
    state = db.get_state()
    mode = state["mode"]
    cursor = state["cursor_index"]

    if mode == "LIBRARIES":
        libraries = await kavita_client.get_libraries()
        return Response(
            content=renderer.render_list_view(
                "LIBRARIES", [library.get("name") for library in libraries], cursor
            ),
            media_type="application/octet-stream",
        )

    elif mode == "SERIES":
        lib_id = state["selected_library_id"]
        items = await kavita_client.get_series(lib_id)

        return Response(
            content=renderer.render_list_view(
                "SELECT SERIES", [series.get("name") for series in items], cursor
            ),
            media_type="application/octet-stream",
        )

    elif mode == "BOOKS":
        series_id = state["selected_series_id"]
        items = await kavita_client.get_series_volumes(series_id)

        return Response(
            content=renderer.render_list_view(
                "SELECT BOOK", [series.get("name") for series in items], cursor
            ),
            media_type="application/octet-stream",
        )

    elif mode == "READER":
        chapter_id = state["selected_book_id"]
        page_num = state["current_page"]
        scroll_step = state["scroll_step"]
        orientation = state["orientation"]
        dither_mode = state["dither_mode"]

        # 1. Handle "Negative Scroll" (User pressed UP at top of page)
        # We need to go to Previous Page -> Bottom
        if scroll_step < 0:
            print("🔄 Scrolling Back to Previous Page...")
            new_page = page_num - 1
            # Fetch prev page HTML to calculate its height
            prev_html = await kavita_client.get_book_page(chapter_id, new_page)
            # Ask engine: "What is the last step index for this html?"
            last_step = await html_engine.render_scroll_view(
                prev_html, -1, renderer, orientation, dither_mode
            )

            # Update DB and Recursively Render
            db.update_state({"current_page": new_page, "scroll_step": last_step})
            return await get_current_view()

        # 2. Fetch Content
        html = await kavita_client.get_book_page(chapter_id, page_num)
        html = html.replace("//192.168.0.4:5000/", "http://192.168.0.4:5000/")

        # 3. Try to Render
        result = await html_engine.render_scroll_view(
            html, scroll_step, renderer, orientation, dither_mode
        )

        # 4. Handle "End of Content" (User pressed DOWN at bottom)
        if result == "NEXT":
            print(f"🔄 Advancing to Next Page (From Page {page_num})")

            # Update DB: Next Page, Reset Scroll to Top
            db.update_state({"current_page": page_num + 1, "scroll_step": 0})
            return await get_current_view()

        # 5. Return Valid Image
        return Response(content=result, media_type="application/octet-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.server_host,
        port=settings.server_port,
        log_level=settings.log_level.lower(),
    )
