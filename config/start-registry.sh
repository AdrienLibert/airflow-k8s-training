#!/usr/bin/env bash
set -euo pipefail

REGISTRY_NAME="${REGISTRY_NAME:-local-registry}"
REGISTRY_PORT="${REGISTRY_PORT:-5000}"

if docker ps --format '{{.Names}}' | grep -qx "$REGISTRY_NAME"; then
  echo "Registry already running: localhost:${REGISTRY_PORT}"
  exit 0
fi

if docker ps -a --format '{{.Names}}' | grep -qx "$REGISTRY_NAME"; then
  docker start "$REGISTRY_NAME" >/dev/null
  echo "Started existing registry: localhost:${REGISTRY_PORT}"
  exit 0
fi

docker run -d \
  -p "${REGISTRY_PORT}:5000" \
  --restart=unless-stopped \
  --name "$REGISTRY_NAME" \
  registry:2

echo "Registry running at localhost:${REGISTRY_PORT}"
