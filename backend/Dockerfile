FROM python:3.12-slim

# ffmpeg is needed for audio processing (WAV validation / format conversion)
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Flush Python stdout/stderr immediately so every log line appears in Render/Docker logs.
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
# Run migrations then start the server.
# LOG_LEVEL in .env / render.yaml controls application log verbosity.
# --log-level warning silences uvicorn's own access logs; application logs go through Python logging.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level warning"]
