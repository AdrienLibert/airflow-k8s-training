#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <patch|minor|major> [--publish]" >&2
  exit 1
}

[[ $# -ge 1 ]] || usage
BUMP="${1}"
case "$BUMP" in
  patch | minor | major) ;;
  *) usage ;;
esac

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
IMAGE_NAME="${IMAGE_NAME:-hello-world-tasks}"

PYTHON="$REPO_ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON=python3
fi

TAG="$("$PYTHON" "$SCRIPT_DIR/scripts/bump_semver.py" "$BUMP" --image-name "$IMAGE_NAME")"
IMAGE="${IMAGE_NAME}:${TAG}"

echo "Building ${IMAGE}..."
docker build -t "$IMAGE" "$SCRIPT_DIR"

# Docker Desktop: cluster nodes don't see host docker images — import into each node.
mapfile -t NODES < <(
  docker ps --format '{{.Names}}' | grep -E '^(desktop-(worker|control-plane)|kind-(worker|control-plane))' || true
)
if [[ ${#NODES[@]} -eq 0 ]]; then
  echo "No local k8s nodes found — skipping image import (OK on single-node Docker Desktop)"
else
  for node in "${NODES[@]}"; do
    echo "Loading ${IMAGE} into ${node}..."
    docker save "$IMAGE" | docker exec -i "$node" ctr -n k8s.io images import -
  done
fi

echo ""
echo "Built ${IMAGE} (Docker Desktop image store)"
echo ""
echo "Publish with:"
echo "  ./dags/scripts/publish-dags.sh --tag ${TAG} --image-name ${IMAGE_NAME}"

if [[ "${2:-}" == "--publish" ]]; then
  "$SCRIPT_DIR/scripts/publish-dags.sh" --tag "$TAG" --image-name "$IMAGE_NAME"
fi
