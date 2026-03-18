FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml README.md .

# Install dependencies
RUN uv sync --no-dev

# Copy source code
COPY src/ src/

# Create data directory
RUN mkdir -p data

# Set environment variables
ENV PYTHONPATH=/app/src

# Run the web server
ENTRYPOINT ["uv", "run", "uvicorn", "forma.__main__:app", "--host", "0.0.0.0", "--port", "8080"]
CMD []
