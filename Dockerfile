FROM --platform=$BUILDPLATFORM python:3.10-alpine AS builder

WORKDIR /app

COPY requirements.txt /app
RUN --mount=type=cache,target=/root/.cache/pip \
    python3 -m pip install -r requirements.txt

COPY . /app

# Add mount point for data volume
# VOLUME /data

ENTRYPOINT ["python3"]
CMD ["main.py"]

FROM builder as dev-envs