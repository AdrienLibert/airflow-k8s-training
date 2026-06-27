#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=registry.sh
source "$SCRIPT_DIR/registry.sh"

TAG="${AIRFLOW_TAG:-3.2.2}"
FULL_IMAGE="$(platform_image_ref "$TAG")"

echo "Building ${FULL_IMAGE}..."
docker build -t "$FULL_IMAGE" "$SCRIPT_DIR"

echo "Pushing ${FULL_IMAGE}..."
docker push "$FULL_IMAGE"
