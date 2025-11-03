# syntax=docker/dockerfile:1

### Build stage ###
FROM python:3.13-alpine AS build

# Install build dependencies for Pillow and other native wheels
RUN apk add --no-cache \
    build-base \
    jpeg-dev zlib-dev freetype-dev

# Copy uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:0.8.21 /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./

# Install dependencies into a virtual environment
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# Copy only app source files
COPY blueprints blueprints
COPY main.py server.py curl.py tools.py mail.py ./
COPY templates templates
COPY data data
COPY pwa pwa
COPY .well-known .well-known

# Clean up caches and pycache
RUN rm -rf /root/.cache/uv
RUN find . -type d -name "__pycache__" -exec rm -rf {} +


### Runtime stage ###
FROM python:3.13-alpine AS runtime
ENV PATH="/app/.venv/bin:$PATH"

# Create non-root user
RUN addgroup -g 1001 appgroup && \
    adduser -D -u 1001 -G appgroup -h /app appuser

WORKDIR /app

# Copy only what’s needed for runtime
COPY --from=build --chown=appuser:appgroup /app/.venv /app/.venv
COPY --from=build --chown=appuser:appgroup /app/blueprints /app/blueprints
COPY --from=build --chown=appuser:appgroup /app/templates /app/templates
COPY --from=build --chown=appuser:appgroup /app/data /app/data
COPY --from=build --chown=appuser:appgroup /app/pwa /app/pwa
COPY --from=build --chown=appuser:appgroup /app/.well-known /app/.well-known
COPY --from=build --chown=appuser:appgroup /app/main.py /app/
COPY --from=build --chown=appuser:appgroup /app/server.py /app/
COPY --from=build --chown=appuser:appgroup /app/curl.py /app/
COPY --from=build --chown=appuser:appgroup /app/tools.py /app/
COPY --from=build --chown=appuser:appgroup /app/mail.py /app/

USER appuser
EXPOSE 5000

ENTRYPOINT ["python3", "main.py"]




# FROM --platform=$BUILDPLATFORM python:3.13-alpine
# COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# # Install curl for healthcheck
# RUN apk add --no-cache curl

# # Set working directory
# WORKDIR /app

# # Install dependencies
# RUN --mount=type=cache,target=/root/.cache/uv \
#     --mount=type=bind,source=uv.lock,target=uv.lock \
#     --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
#     uv sync --locked --no-install-project

# # Copy the project into the image
# ADD . /app

# # Sync the project
# RUN --mount=type=cache,target=/root/.cache/uv \
#     uv sync --locked

# # Add mount point for data volume
# # VOLUME /data

# ENTRYPOINT ["uv", "run"]
# CMD ["main.py"]
