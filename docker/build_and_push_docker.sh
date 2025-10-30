#!/usr/bin/env bash

set -euo pipefail

# Build and push multi-arch Docker image using buildx, per README
# Optional:
#   VERSION       (e.g., 1.0.0). If omitted, only :latest is pushed
#   DOCKER_TOKEN  (if login non-interactive; otherwise you will be prompted)

# Script is in ./docker; build context should be repo root one level up
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCKERFILE_PATH="${ROOT_DIR}/docker/Dockerfile"
DOCKER_USER="mnbactabio"
DOCKER_IMAGE="bacta-apps"

if [[ ! -f "${DOCKERFILE_PATH}" ]]; then
  echo "Error: Dockerfile not found at ${DOCKERFILE_PATH}" >&2
  exit 1
fi

if [[ -z "${DOCKER_USER:-}" ]]; then
  echo "Error: DOCKER_USER is required (e.g., export DOCKER_USER=\"mnbactabio\")" >&2
  exit 1
fi

if [[ -z "${IMAGE:-}" ]]; then
  echo "Error: IMAGE is required (e.g., export IMAGE=\"bacta-apps\")" >&2
  exit 1
fi

TAGS=("${DOCKER_USER}/${IMAGE}:latest")
if [[ -n "${VERSION:-}" ]]; then
  TAGS+=("${DOCKER_USER}/${IMAGE}:${VERSION}")
fi

echo "Using tags: ${TAGS[*]}"

# Ensure buildx is available
if ! docker buildx version >/dev/null 2>&1; then
  echo "Error: docker buildx is not available. Install Docker Buildx plugin." >&2
  exit 1
fi

# Create or select a multi-arch builder
if ! docker buildx inspect multi-arch-builder >/dev/null 2>&1; then
  docker buildx create --name multi-arch-builder --use >/dev/null
else
  docker buildx use multi-arch-builder >/dev/null
fi

# Build and push
BUILD_CMD=(
  docker buildx build
  -f "${DOCKERFILE_PATH}"
  --platform linux/amd64,linux/arm64
)

for tag in "${TAGS[@]}"; do
  BUILD_CMD+=( -t "${tag}" )
done

BUILD_CMD+=( --push "${ROOT_DIR}" )

echo "Running: ${BUILD_CMD[*]}"
"${BUILD_CMD[@]}"

echo "Done. Published tags: ${TAGS[*]}"