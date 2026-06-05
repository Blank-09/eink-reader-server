# ESP32 Kavita Reader Backend

A modular FastAPI backend server that fetches light novels from Kavita (v0.8.7.0+) and converts them to 4-bit images optimized for ESP32 e-paper displays.

## Installation

### Using UV (Recommended)

```bash
# Install UV if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
uv sync
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
# Using uv
uv run main.py

# Or using the script
python main.py
```

### Format code

```bash
black .
ruff check --fix .
```

## Troubleshooting

**Authentication fails:**

- Verify Kavita server is running at the specified URL
- Check your API key is correct (get it from Kavita Settings → Users → API Keys)
- Look at server logs for detailed error messages

**Images look bad:**

- Adjust font size in .env (try 14-20)
- Check display dimensions match your e-paper (400x300 for 4.2")
- For manga/images, ensure source images are high quality

**Server crashes:**

- Check Kavita server is accessible: `curl http://localhost:5000`
- Verify chapter IDs are valid
- Check server logs: `uv run main.py` shows detailed errors

## License

MIT

## Contributing

Pull requests welcome! Please ensure code is formatted with Black and passes Ruff linting.
