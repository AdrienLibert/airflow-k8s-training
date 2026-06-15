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

echo ""
echo "Built ${IMAGE} (Docker Desktop image store)"
echo ""
echo "Publish with:"
echo "  ./dags/scripts/publish-dags.sh --tag ${TAG} --image-name ${IMAGE_NAME}"

if [[ "${2:-}" == "--publish" ]]; then
  "$SCRIPT_DIR/scripts/publish-dags.sh" --tag "$TAG" --image-name "$IMAGE_NAME"
fi
