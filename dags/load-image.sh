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
REGISTRY="${REGISTRY:-localhost:5000}"
K8S_REGISTRY="${K8S_REGISTRY:-host.docker.internal:5000}"
IMAGE_NAME="${IMAGE_NAME:-hello-world-tasks}"

if ! docker ps --format '{{.Names}}' | grep -qx "${REGISTRY_NAME:-local-registry}"; then
  echo "ERROR: local registry is not running. Start it first:" >&2
  echo "  ./config/start-registry.sh" >&2
  exit 1
fi

PYTHON="$REPO_ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON=python3
fi

TAG="$("$PYTHON" "$SCRIPT_DIR/scripts/bump_semver.py" "$BUMP" --registry "$REGISTRY" --image-name "$IMAGE_NAME")"
LOCAL_IMAGE="${REGISTRY}/${IMAGE_NAME}:${TAG}"

echo "Building ${LOCAL_IMAGE}..."
docker build -t "$LOCAL_IMAGE" "$SCRIPT_DIR"

echo "Pushing ${LOCAL_IMAGE}..."
docker push "$LOCAL_IMAGE"

echo ""
echo "Built and pushed: ${LOCAL_IMAGE}"
echo "Kubernetes image: ${K8S_REGISTRY}/${IMAGE_NAME}:${TAG}"
echo ""
echo "Publish with:"
echo "  ./dags/scripts/publish-dags.sh --tag ${TAG}"

if [[ "${2:-}" == "--publish" ]]; then
  "$SCRIPT_DIR/scripts/publish-dags.sh" --tag "$TAG" --registry "$K8S_REGISTRY"
fi
