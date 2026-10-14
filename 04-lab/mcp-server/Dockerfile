# Use official uv image with Python 3.12
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set working directory
WORKDIR /app

# Enable bytecode compilation and unbuffered stdout
ENV UV_COMPILE_BYTECODE=1
ENV PYTHONUNBUFFERED=1

# Default port for MCP Server (matches MCP_SERVER_URL=http://localhost:8085/mcp in client)
ENV PORT=8085

# Copy dependency definition
COPY pyproject.toml ./

# Install dependencies into system environment using uv
RUN uv pip install --no-cache --system -r pyproject.toml

# Copy application code
COPY weather.py ./

# Expose port (8085 by default, Cloud Run overrides PORT to 8080)
EXPOSE 8085

# Start MCP server
CMD ["python", "weather.py"]
