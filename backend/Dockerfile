# Use an official Python runtime as a parent image
FROM python:3.9-slim
# # Use PyTorch base image with CUDA support
# FROM pytorch/pytorch:2.2.0-cuda12.1-cudnn8-runtime

# # Set environment variables
# ENV PYTHONDONTWRITEBYTECODE=1
# ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies and uv
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && /root/.local/bin/uv --version \
    && ln -s /root/.local/bin/uv /usr/local/bin/uv

# Create models directory
RUN mkdir -p /app/models && chmod 777 /app/models

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies using uv
RUN uv pip install --system --requirement requirements.txt

# Copy source code
COPY . .

# Create volume mount point for model weights and checkpoints
VOLUME /app/models

# Expose the port
EXPOSE 8000

# # Health check
# HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
#     CMD curl -f http://localhost:8000/api/health || exit 1

# Start the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"] 