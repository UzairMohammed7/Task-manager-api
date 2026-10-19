FROM python:3.12-slim

# No .pyc clutter; logs appear immediately instead of being buffered.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /code

# Copy ONLY requirements first: Docker caches this layer, so rebuilds after a
# code change skip the slow dependency install.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Run as an unprivileged user, never root.
RUN useradd --create-home --uid 1000 appuser

COPY app ./app
USER appuser

EXPOSE 8000

# No --reload here: that is a development-only flag.
# 0.0.0.0 is required inside a container; 127.0.0.1 would be unreachable from outside.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]