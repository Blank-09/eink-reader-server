# Use the official Playwright image which includes Python and browser dependencies
# We match the version to your pyproject.toml (v1.49.0+ is widely compatible)
FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

WORKDIR /app

# 1. Install system-level build tools (needed for some python packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 2. Copy project definition
COPY pyproject.toml .

# 3. Install Python dependencies
# We install directly from pyproject.toml. 
# We also run 'playwright install' just to be safe, though the base image usually has them.
RUN pip install --no-cache-dir . && \
    playwright install chromium

# 4. Copy the application code
COPY . .

# 5. Expose the port
EXPOSE 8000

# 6. Run the server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
