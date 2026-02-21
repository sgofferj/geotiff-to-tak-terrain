FROM python:3.10-slim

# Install GDAL dependencies
RUN apt-get update && apt-get install -y --no-install-recommends
    libgdal-dev
    g++
    && rm -rf /var/lib/apt/lists/*

# Set GDAL environment variables
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Install Poetry
RUN pip install --no-cache-dir poetry

WORKDIR /app

# Copy project files
COPY pyproject.toml poetry.lock README.md ./
COPY src/ ./src/

# Install dependencies
RUN poetry config virtualenvs.create false
    && poetry install --no-interaction --no-ansi --only main

# Set entrypoint
ENTRYPOINT ["poetry", "run", "geotiff-to-tak-terrain"]
