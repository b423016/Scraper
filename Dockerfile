FROM python:3.12-slim

# Install system dependencies (yt-dlp sometimes requires ffmpeg for advanced extractions)
RUN apt-get update && apt-get install -y ffmpeg curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. Copy backend requirements and install
COPY backend/requirements.txt ./backend/
# We need to install the dependencies in the global python environment of the container
RUN pip install --no-cache-dir -r backend/requirements.txt
# Ensure nltk is installed with newspaper4k
RUN pip install --no-cache-dir "newspaper4k[nlp]"

# 2. Copy the entire project (backend + frontend)
COPY . .

# 3. Pre-download the embedding model so it's baked into the Docker image
# This prevents it from downloading on every server start
WORKDIR /app/backend
RUN python -c "from models.embedding_service import download_model; download_model()"

# 4. Expose the port (Render sets the PORT environment variable)
EXPOSE 8000

# 5. Start the FastAPI server
# We use $PORT if Render provides it, otherwise default to 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
