# Video Pipeline - Python 3.11 with ffmpeg
FROM python:3.11-slim

# System deps: ffmpeg, espeak-ng (for edge-tts), libs for pillow, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    espeak-ng \
    libespeak-ng1 \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY pyproject.toml constraints.txt ./
RUN pip install --no-cache-dir -e . --constraint=constraints.txt

# Copy source
COPY src ./src
COPY ../shared ./shared

# Non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

ENTRYPOINT ["python", "-m", "src.main"]
CMD ["--help"]