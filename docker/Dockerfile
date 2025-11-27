# ---------- Base stage with common deps ----------
FROM python:3.12-slim AS base

WORKDIR /app

# Switch APT sources to HTTPS for Debian Bookworm+ and install system deps (including geospatial libraries)
RUN find /etc/apt/sources.list.d/ -type f -name "*.sources" \
        -exec sed -i 's|http://deb.debian.org|https://deb.debian.org|g' {} \; && \
    apt-get update && apt-get install -y \
        ca-certificates \
        gcc \
        g++ \
        curl \
        libffi-dev \
        gdal-bin \
        libgdal-dev \
        libspatialindex-dev \
        libgeos-dev \
        libproj-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy dependency files once for caching
COPY pyproject.toml uv.lock ./

# Install Python deps (no app code yet to leverage layer caching)
RUN uv sync --frozen

# ---------- API stage ----------
FROM base AS api

# Copy application code
COPY api/ ./api/
COPY isolysis/ ./isolysis/
COPY .env* ./

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]

# ---------- Streamlit stage ----------
FROM base AS streamlit

# Copy application code
COPY api/ ./api/
COPY isolysis/ ./isolysis/
COPY st_*.py ./
COPY .env* ./

EXPOSE 8501
CMD ["uv", "run", "streamlit", "run", "st_app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
