# MAX Bot with Mistral AI Integration
# Based on Python 3.11

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Create config directory
RUN mkdir -p /app/config

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY bot.py .

# Copy default config (can be overridden by mounted volume)
COPY bot.conf /app/config/bot.conf

# Create config directory with proper permissions for mounted volumes
RUN mkdir -p /app/config && chmod 777 /app/config

# Run as non-root user for security
RUN useradd -m botuser
USER botuser

# Expose port (not strictly needed for polling, but good practice)
EXPOSE 80

# Command to run the bot
CMD ["python", "bot.py"]
