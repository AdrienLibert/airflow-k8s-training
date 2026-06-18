#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 [patch|minor|major]" >&2
  echo "  Build hello-world-converter. With a bump level, tag from Docker semver." >&2
  echo "  Without a bump level, tag :latest" >&2
  exit 1
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
IMAGE_NAME="${IMAGE_NAME:-hello-world-converter}"

if [[ $# -eq 0 ]]; then
  TAG="latest"
elif [[ $# -eq 1 ]]; then
  case "$1" in
    patch | minor | major) ;;
    *) usage ;;
  esac
  PYTHON="$REPO_ROOT/.venv/bin/python"
  if [[ ! -x "$PYTHON" ]]; then
    PYTHON=python3
  fi
  TAG="$("$PYTHON" "$REPO_ROOT/dags/scripts/bump_semver.py" "$1" --image-name "$IMAGE_NAME")"
else
  usage
fi

IMAGE="${IMAGE_NAME}:${TAG}"

echo "Building ${IMAGE}..."
docker build -t "$IMAGE" "$SCRIPT_DIR"

echo ""
echo "Built ${IMAGE} (Docker Desktop image store)"
