# Collector - Python 3.11 slim
FROM python:3.11-slim

# System deps for newsplease, lxml, pillow, ffmpeg (para video se necessário)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt-dev \
    libjpeg-dev \
    zlib1g-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (cache layer)
COPY pyproject.toml constraints.txt ./
RUN pip install --no-cache-dir -e . --constraint=constraints.txt

# Copy source
COPY src ./src
COPY ../shared ./shared

# Non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Default command
ENTRYPOINT ["python", "-m", "src.pipeline"]
CMD ["--help"]