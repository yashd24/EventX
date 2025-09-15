FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
        netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Create directories for static, media, and logs files
RUN mkdir -p /app/staticfiles /app/mediafiles /app/logs

# Make manage.py executable
RUN chmod +x /app/manage.py

# Collect static files (with proper logging directory)
RUN python manage.py collectstatic --noinput --clear || true

# Copy entrypoint script
COPY ./entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

# Run entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
