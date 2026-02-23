FROM python:3.10-slim

# Install GDAL dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal-dev \
    python3-dev \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set GDAL environment variables
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Install Poetry
RUN pip install --no-cache-dir poetry

WORKDIR /app

# Copy project files
COPY pyproject.toml README.md ./

# Install numpy and GDAL bindings matching the system version
RUN pip install numpy==1.26.0 && \
    GDAL_VERSION=$(gdal-config --version) && \
    pip install GDAL==$GDAL_VERSION

# Install remaining dependencies via poetry
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --only main --no-root

COPY src/ ./src/
RUN pip install .

# Set entrypoint
ENTRYPOINT ["geotiff-to-tak-terrain"]
