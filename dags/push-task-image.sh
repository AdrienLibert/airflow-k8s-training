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

GENERATED="$(mktemp -d)"
cleanup() { rm -rf "$GENERATED"; }
trap cleanup EXIT

echo "Validating DAG definitions..."
"$PYTHON" "$SCRIPT_DIR/scripts/validate.py"

echo "Checking DAG generation for ${IMAGE}..."
"$PYTHON" "$SCRIPT_DIR/scripts/generate_dags.py" \
  --tag "$TAG" \
  --image-name "$IMAGE_NAME" \
  --output-dir "$GENERATED"
shopt -s nullglob
py_files=("$GENERATED"/*.py)
shopt -u nullglob
[[ ${#py_files[@]} -gt 0 ]] || { echo "ERROR: generator produced no DAG files" >&2; exit 1; }
"$PYTHON" -m py_compile "${py_files[@]}"

echo "Building ${IMAGE}..."
docker build -t "$IMAGE" "$SCRIPT_DIR"

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

if [[ "${2:-}" == "--publish" ]]; then
  "$SCRIPT_DIR/publish-dags.sh" --tag "$TAG" --image-name "$IMAGE_NAME"
else
  echo ""
  echo "Deploy DAGs with:"
  echo "  ./dags/publish-dags.sh --tag ${TAG} --image-name ${IMAGE_NAME}"
fi
