# --- Stage 1: Build the Frontend ---
FROM node:20-slim AS frontend-builder
WORKDIR /app/caren-ui

# Copy only package files first for better caching
COPY caren-ui/package*.json ./
RUN npm install

# Copy the rest of the frontend and build
COPY caren-ui/ ./
RUN npm run build

# --- Stage 2: Final Backend Image ---
FROM python:3.10-slim
WORKDIR /app

# Install system dependencies (ffmpeg is crucial for voice/audio)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend source code
COPY . .

# Copy the built frontend from Stage 1 into the expected directory
COPY --from=frontend-builder /app/caren-ui/dist ./caren-ui/dist

# Expose port 8000 for FastAPI
EXPOSE 8000

# Environment variables (Defaults - can be overridden at runtime)
# IMPORTANT: OLLAMA_MODEL should match what you have in your local Ollama instance
ENV OLLAMA_MODEL=llama2
ENV SMTP_PORT=465
ENV SMTP_SERVER=smtp.gmail.com
# Set OLLAMA_HOST if running Ollama in a separate container or on the host
# ENV OLLAMA_HOST=http://host.docker.internal:11434

# Start the application
CMD ["python", "main_api.py"]
