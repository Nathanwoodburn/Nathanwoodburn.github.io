# syntax=docker/dockerfile:1

### Build stage ###
FROM python:3.13-alpine AS build

# Install build dependencies for Pillow and other native wheels
# Kept in case source builds are needed, though wheels are preferred
RUN apk add --no-cache \
    build-base \
    jpeg-dev zlib-dev freetype-dev

# Copy uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:0.8.21 /uv /uvx /bin/

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies into a virtual environment
# - --frozen: strict lockfile usage
# - --no-dev: exclude development dependencies
# - --no-install-project: avoid installing app as package
# - --compile-bytecode: ensuring .pyc files for startup speed (optional, omit if size is critical but usually worth it)
# We omit --compile-bytecode here to save space as requested
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --no-install-workspace

### PDF Build stage (isolated so chromium is not in final image) ###
FROM python:3.13-alpine AS pdf-builder

# Install chromium and fonts only for PDF generation in this intermediate stage
RUN apk add --no-cache chromium font-noto

WORKDIR /app

COPY --from=build /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Only copy files required for resume PDF generation to maximize layer caching
COPY tools.py ./
COPY data/resume.json data/resume.json
COPY templates/resume.html templates/resume.html
COPY templates/resume.ascii templates/resume.ascii
COPY templates/assets templates/assets

# Generate the PDF files during build
RUN python3 tools.py --build-resume

### Runtime stage ###
FROM python:3.13-alpine AS runtime

ENV PATH="/app/.venv/bin:$PATH"

# Create non-root user and install curl for healthchecks
RUN addgroup -g 1001 appgroup && \
    adduser -D -u 1001 -G appgroup -h /app appuser && \
    apk add --no-cache curl

WORKDIR /app

# Copy the virtual environment from build stage
COPY --from=build --chown=appuser:appgroup /app/.venv /app/.venv

# Copy application directories and assets
COPY --chown=appuser:appgroup blueprints blueprints
COPY --chown=appuser:appgroup templates templates
COPY --chown=appuser:appgroup data data
# Overlay pre-built PDFs from pdf-builder
COPY --from=pdf-builder --chown=appuser:appgroup /app/data/resume.pdf data/resume.pdf
COPY --from=pdf-builder --chown=appuser:appgroup /app/data/resume_support.pdf data/resume_support.pdf
COPY --chown=appuser:appgroup pwa pwa
COPY --chown=appuser:appgroup .well-known .well-known
# Copy top-level Python files
COPY --chown=appuser:appgroup *.py ./

USER appuser
EXPOSE 5000

ENTRYPOINT ["python3", "main.py"]
