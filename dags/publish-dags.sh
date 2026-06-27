#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 --tag <semver> --image-name <name>" >&2
  exit 1
}

TAG=""
IMAGE_NAME=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tag)
      [[ $# -ge 2 ]] || usage
      TAG="$2"
      shift 2
      ;;
    --image-name)
      [[ $# -ge 2 ]] || usage
      IMAGE_NAME="$2"
      shift 2
      ;;
    *)
      usage
      ;;
  esac
done

[[ -n "$TAG" && -n "$IMAGE_NAME" ]] || usage

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS_DIR="$SCRIPT_DIR/scripts"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
NAMESPACE="${NAMESPACE:-airflow}"

# shellcheck source=../config/registry.sh
source "$REPO_ROOT/config/registry.sh"

GENERATED="$(mktemp -d)"
cleanup() { rm -rf "$GENERATED"; }
trap cleanup EXIT

PYTHON="$REPO_ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON=python3
fi

FULL_IMAGE="$(task_image_ref "$TAG")"

"$PYTHON" "$SCRIPTS_DIR/generate_dags.py" \
  --image "$FULL_IMAGE" \
  --tag "$TAG" \
  --image-name "$IMAGE_NAME" \
  --output-dir "$GENERATED"

shopt -s nullglob
py_files=("$GENERATED"/*.py)
shopt -u nullglob
[[ ${#py_files[@]} -gt 0 ]] || { echo "ERROR: generator produced no DAG files" >&2; exit 1; }

POD="$(kubectl get pod -n "$NAMESPACE" -l component=dag-processor -o jsonpath='{.items[0].metadata.name}')"

for py in "${py_files[@]}"; do
  name="$(basename "$py")"
  echo "Publishing $name to $POD..."
  kubectl cp "$py" "$NAMESPACE/$POD:/opt/airflow/dags/$name" -c dag-processor
done

echo "Published ${#py_files[@]} DAG file(s) using ${IMAGE_NAME}:${TAG}."
