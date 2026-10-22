# syntax=docker/dockerfile:1

### Dependency build stage ###
FROM python:3.13-alpine AS build

# Copy uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:0.8.21 /uv /uvx /bin/

WORKDIR /app

# Install dependencies into a virtual environment
# Pre-built musllinux wheels are available for all dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --no-install-workspace

### PDF Build stage (completely independent from build stage, runs in parallel) ###
FROM python:3.13-alpine AS pdf-builder

# Install chromium and fonts only for PDF generation in this intermediate stage
RUN apk add --no-cache chromium font-noto

# Install only jinja2 needed for rendering resume templates
COPY --from=ghcr.io/astral-sh/uv:0.8.21 /uv /bin/uv
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system jinja2

WORKDIR /app

# Only copy files strictly required for resume PDF generation to maximize layer caching
COPY build_resume.py ./
COPY data/resume.json data/resume.json
COPY templates/resume.html templates/resume.html
COPY templates/assets templates/assets

# Generate the PDF files during build
RUN python3 build_resume.py

### Runtime stage ###
FROM python:3.13-alpine AS runtime

ENV PATH="/app/.venv/bin:$PATH"

# Create non-root user and install curl for healthchecks
RUN addgroup -g 1001 appgroup && \
    adduser -D -u 1001 -G appgroup -h /app appuser && \
    apk add --no-cache curl

WORKDIR /app

# Copy the virtual environment from build stage using --link for independent caching
COPY --link --from=build --chown=1001:1001 /app/.venv /app/.venv

# Copy application directories and assets using --link
COPY --link --chown=1001:1001 blueprints blueprints
COPY --link --chown=1001:1001 templates templates
COPY --link --chown=1001:1001 data data
# Overlay pre-built PDFs from pdf-builder
COPY --link --from=pdf-builder --chown=1001:1001 /app/data/resume.pdf data/resume.pdf
COPY --link --from=pdf-builder --chown=1001:1001 /app/data/resume_support.pdf data/resume_support.pdf
COPY --link --chown=1001:1001 pwa pwa
COPY --link --chown=1001:1001 .well-known .well-known
# Copy top-level Python files
COPY --link --chown=1001:1001 *.py ./

USER appuser
EXPOSE 5000

ENTRYPOINT ["python3", "main.py"]
