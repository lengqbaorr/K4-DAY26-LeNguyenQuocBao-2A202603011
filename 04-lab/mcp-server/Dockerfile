# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy application and dependency metadata before installing
COPY pyproject.toml weather.py ./

# Install dependencies
RUN pip install --no-cache-dir .

# Expose port (Cloud Run will override this)
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "weather.py"]
