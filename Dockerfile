FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml .

# Install dependencies
RUN uv sync --no-dev

# Copy source code
COPY src/ src/

# Create data directory
RUN mkdir -p data

# Set environment variables
ENV PYTHONPATH=/app/src
ENV DATABASE_PATH=/app/data/fitness_coach.db

# Run the CLI
ENTRYPOINT ["uv", "run", "fitness-coach"]
CMD ["--help"]
