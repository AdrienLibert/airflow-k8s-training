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
# shellcheck source=../config/registry.sh
source "$REPO_ROOT/config/registry.sh"

PYTHON="$REPO_ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON=python3
fi

TAG="$("$PYTHON" "$SCRIPT_DIR/scripts/bump_semver.py" "$BUMP" --image-name "$IMAGE_NAME")"
FULL_IMAGE="$(task_image_ref "$TAG")"

GENERATED="$(mktemp -d)"
cleanup() { rm -rf "$GENERATED"; }
trap cleanup EXIT

echo "Validating DAG definitions..."
"$PYTHON" "$SCRIPT_DIR/scripts/validate.py"

echo "Checking DAG generation for ${FULL_IMAGE}..."
"$PYTHON" "$SCRIPT_DIR/scripts/generate_dags.py" \
  --image "$FULL_IMAGE" \
  --tag "$TAG" \
  --image-name "$IMAGE_NAME" \
  --output-dir "$GENERATED"
shopt -s nullglob
py_files=("$GENERATED"/*.py)
shopt -u nullglob
[[ ${#py_files[@]} -gt 0 ]] || { echo "ERROR: generator produced no DAG files" >&2; exit 1; }
"$PYTHON" -m py_compile "${py_files[@]}"

echo "Building ${FULL_IMAGE}..."
docker build -t "$FULL_IMAGE" "$SCRIPT_DIR"

if should_push_images; then
  echo "Pushing ${FULL_IMAGE}..."
  docker push "$FULL_IMAGE"
else
  echo "Skipping push (${DEPLOY_PROFILE} profile — image stays in local Docker store)."
fi

if [[ "${2:-}" == "--publish" ]]; then
  "$SCRIPT_DIR/publish-dags.sh" --tag "$TAG" --image-name "$IMAGE_NAME"
else
  echo ""
  echo "Deploy DAGs with:"
  echo "  ./dags/publish-dags.sh --tag ${TAG} --image-name ${IMAGE_NAME}"
fi
