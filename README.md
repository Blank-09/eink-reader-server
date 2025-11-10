# ESP32 Kavita Reader Backend

A modular FastAPI backend server that fetches light novels from Kavita (v0.8.7.0+) and converts them to 1-bit images optimized for ESP32 e-paper displays.

## 🎯 Features

- 🔐 Kavita API authentication via API key
- 📚 Fetch libraries, series, and chapters from Kavita
- 📖 Support for both text (EPUB/PDF) and image-based (manga/comics) chapters
- 🖼️ Convert text to 1-bit images with word wrapping
- 🎨 Convert images to 1-bit format with Floyd-Steinberg dithering
- ⚡ Multiple output formats: PNG (preview), raw bytes (ESP32), hex string (debug)
- 📊 Reading progress tracking and bookmarks
- 🔧 Fully modular and configurable
- 🚀 Fast API with async/await support
- 📱 Optimized for 4.2" e-paper displays (400x300)

## Project Structure

```
esp32-kavita-reader/
├── main.py              # FastAPI application entry point
├── kavita_client.py     # Kavita API client module
├── image_processor.py   # Image processing and conversion
├── models.py            # Pydantic models for API responses
├── config.py            # Configuration management
├── pyproject.toml       # UV/pip dependencies
├── .env.example         # Example environment variables
└── README.md            # This file
```

## Installation

### Using UV (Recommended)

```bash
# Install UV if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

### Using pip

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

## Configuration

1. **Get your Kavita API Key:**

   - Open Kavita web interface
   - Go to **Settings** → **Users**
   - Click on your user → **API Keys**
   - Create a new API key
   - Copy the generated key

2. Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

3. Edit `.env` with your Kavita API key:

```bash
KAVITA_BASE_URL=http://localhost:5000
KAVITA_API_KEY=your_actual_api_key_here
KAVITA_PLUGIN_NAME=ESP32Reader

# Display settings for your 4.2" display
DISPLAY_WIDTH=400
DISPLAY_HEIGHT=300
FONT_SIZE=16
```

## Usage

### Start the server

```bash
# Using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or using the script
python main.py
```

### API Endpoints

#### Get Libraries

```bash
GET /libraries
```

Returns all available libraries from Kavita.

#### Get Series

```bash
GET /series/{library_id}
```

Returns all series in a specific library.

#### Get Chapters

```bash
GET /chapters/{series_id}
```

Returns all chapters for a series.

#### Get Chapter as Image (Text)

```bash
GET /chapter/text/{chapter_id}?page=0&format=png
```

Renders chapter text as a 1-bit image.

**Query Parameters:**

- `page` (int): Page number (default: 0)
- `format` (string): Output format - `png`, `raw`, or `hex` (default: png)

**Response Formats:**

- `png`: PNG image file
- `raw`: Raw bytes (1 bit per pixel, packed)
- `hex`: JSON with hex string and dimensions

#### Get Chapter Image

```bash
GET /chapter/image/{chapter_id}?format=png
```

Converts chapter images to 1-bit format.

**Query Parameters:**

- `format` (string): Output format - `png`, `raw`, or `hex` (default: png)

### Example ESP32 Request

```cpp
// ESP32 Arduino code example
HTTPClient http;
http.begin("http://your-server:8000/chapter/text/123?format=raw");
int httpCode = http.GET();

if (httpCode == HTTP_CODE_OK) {
    WiFiClient * stream = http.getStreamPtr();
    // Read raw bytes directly to display buffer
    stream->readBytes(displayBuffer, bufferSize);
    display.drawBitmap(displayBuffer);
}
```

## Module Details

### kavita_client.py

Handles all communication with the Kavita API:

- Authentication using API key (via `/api/Plugin/authenticate`)
- Fetching libraries, series, volumes, chapters
- Downloading chapter pages (for image-based content)
- Fetching book resources (for text-based content like EPUB)
- Reading progress tracking

### image_processor.py

Processes text and images for e-paper displays:

- Text-to-image conversion with word wrapping
- Image-to-1-bit conversion with Floyd-Steinberg dithering
- Multiple output formats (PNG, raw bytes, hex)

### models.py

Pydantic models for type-safe API responses:

- Library, Series, Chapter models
- Image format enum
- Response validation

### config.py

Centralized configuration using pydantic-settings:

- Environment variable loading
- Default values
- Type validation

## Development

### Run tests

```bash
uv pip install -e ".[dev]"
pytest
```

### Format code

```bash
black .
ruff check --fix .
```

## ESP32 Integration Tips

1. **Display Size**: Adjust `DISPLAY_WIDTH` and `DISPLAY_HEIGHT` to match your e-paper display
2. **Font Size**: Larger fonts are more readable but show less text per page
3. **Raw Format**: Use `format=raw` for most efficient transfer to ESP32
4. **Memory**: Raw format for 400x300 display = 15,000 bytes (400\*300/8)
5. **Pagination**: Use the `page` parameter to navigate through long texts

## Common Display Sizes

- **2.9" e-Paper**: 296x128
- **4.2" e-Paper**: 400x300
- **7.5" e-Paper**: 800x480

## Troubleshooting

**Authentication fails:**

- Verify Kavita server is running at the specified URL
- Check your API key is correct (get it from Kavita Settings → Users → API Keys)
- Look at server logs for detailed error messages

**"Unable to determine which files to ship":**

- Make sure all `__init__.py` files exist in modules/
- Run `uv sync` again after creating the files

**Images look bad:**

- Adjust font size in .env (try 14-20)
- Check display dimensions match your e-paper (400x300 for 4.2")
- For manga/images, ensure source images are high quality

**Server crashes:**

- Check Kavita server is accessible: `curl http://localhost:5000`
- Verify chapter IDs are valid
- Check server logs: `uv run python main.py` shows detailed errors
- Some chapters might be image-based vs text-based - use the correct endpoint

## License

MIT

## Contributing

Pull requests welcome! Please ensure code is formatted with Black and passes Ruff linting.
