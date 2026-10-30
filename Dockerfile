FROM ghcr.io/osgeo/gdal:ubuntu-small-3.11.4

# Enable pip (the GDAL image ships without it) and install Poetry
RUN apt-get update && apt-get install -y --no-install-recommends python3-pip \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --break-system-packages --no-cache-dir poetry

WORKDIR /app

# Copy project files
COPY pyproject.toml README.md poetry.lock ./

# Install remaining dependencies via poetry (GDAL and numpy come from the base image)
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --only main --no-root

COPY src/ ./src/
RUN pip install --break-system-packages --no-cache-dir .

# Set entrypoint
ENTRYPOINT ["geotiff-to-tak-terrain"]
