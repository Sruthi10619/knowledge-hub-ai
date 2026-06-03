# ==============================================================================
# MULTI-STAGE DOCKERFILE: UNIFIED REACT + FASTAPI DEPLOYMENT
# Optimized for free deployment on Hugging Face Spaces (Port 7860, writable data paths).
# ==============================================================================

# --- STAGE 1: COMPILING FRONTEND SPA ---
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

# Copy frontend source files & config
COPY frontend/package*.json ./
COPY frontend/tsconfig*.json ./
COPY frontend/vite.config.ts ./
COPY frontend/tailwind.config.js ./
COPY frontend/postcss.config.js ./
COPY frontend/index.html ./

# Install dependencies (ignoring scripts for speed and security)
RUN npm install

# Copy source directories
COPY frontend/src ./src

# Build static bundle (emits into ../backend/static via vite config outDir override)
RUN npm run build


# --- STAGE 2: BACKEND SERVER & APP SHELL ---
FROM python:3.10-slim AS final
WORKDIR /app

# Install system dependencies (build tools for tokenizers / C extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend dependencies listing
COPY backend/requirements.txt ./backend/

# Install python dependencies in system scope
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend code
COPY backend/app ./backend/app

# Copy compiled frontend assets from Stage 1 into the static server directory
COPY --from=frontend-builder /app/backend/static ./backend/static

# Setup data storage paths (Must be inside container workspace for HF Spaces)
ENV DATA_DIR=/app/backend/data
RUN mkdir -p $DATA_DIR/db $DATA_DIR/chroma $DATA_DIR/logs && chmod -R 777 $DATA_DIR

# Set environment defaults for Hugging Face Spaces deployment
ENV DEPLOYMENT_MODE=hf-spaces
ENV PORT=7860
ENV HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/backend

EXPOSE 7860

# CMD executes uvicorn starting FastAPI on Hugging Face Space port

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
