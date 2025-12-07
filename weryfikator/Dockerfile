FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies (without lock file)
RUN uv sync

# Copy the application code
COPY . .

# Add virtualenv to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Run the application using uv run
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8888"]
