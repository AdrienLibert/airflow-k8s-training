#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REGISTRY="${REGISTRY:-local}"
TAG="${TAG:-3.2.2}"
IMAGE="${REGISTRY}/airflow:${TAG}"

docker build -t "$IMAGE" "$SCRIPT_DIR"

if [[ "${1:-}" == "--push" ]]; then
  docker push "$IMAGE"
  exit 0
fi

# Docker Desktop: cluster nodes don't see host docker images — import into each node.
mapfile -t NODES < <(
  docker ps --format '{{.Names}}' | grep -E '^(desktop-(worker|control-plane)|kind-(worker|control-plane))' || true
)
if [[ ${#NODES[@]} -eq 0 ]]; then
  echo "No local k8s nodes found — skipping image import (OK on single-node Docker Desktop)"
  exit 0
fi

for node in "${NODES[@]}"; do
  echo "Loading $IMAGE into $node..."
  docker save "$IMAGE" | docker exec -i "$node" ctr -n k8s.io images import -
done
