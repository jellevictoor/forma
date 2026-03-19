FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml README.md .

# Install dependencies (without the project itself)
RUN uv sync --no-dev --no-install-project

# Copy source code and migrations
COPY src/ src/
COPY migrations/ migrations/

# Install project in editable mode so watch-synced source is used directly
RUN uv pip install -e . --no-deps

# Create data directory
RUN mkdir -p data

# Set environment variables
ENV PYTHONPATH=/app/src

# Run the web server
ENTRYPOINT ["uv", "run", "uvicorn", "forma.__main__:app", "--host", "0.0.0.0", "--port", "8080"]
CMD []
