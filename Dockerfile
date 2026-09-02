FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
WORKDIR /app
COPY pyproject.toml ./
RUN uv sync --no-dev
COPY generate_icon.py ./
COPY app ./app
COPY static ./static
# Generate the apple-touch-icon.png (180x180) from the same skull design
RUN python3 generate_icon.py
EXPOSE 8000
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]