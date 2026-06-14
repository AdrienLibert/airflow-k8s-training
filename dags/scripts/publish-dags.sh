#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 --tag <semver> [--registry host.docker.internal:5000] [--image-name hello-world-tasks]" >&2
  exit 1
}

TAG=""
REGISTRY="${K8S_REGISTRY:-host.docker.internal:5000}"
IMAGE_NAME="${IMAGE_NAME:-hello-world-tasks}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tag)
      [[ $# -ge 2 ]] || usage
      TAG="$2"
      shift 2
      ;;
    --registry)
      [[ $# -ge 2 ]] || usage
      REGISTRY="$2"
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

[[ -n "$TAG" ]] || usage

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DAGS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$DAGS_ROOT/.." && pwd)"
NAMESPACE="${NAMESPACE:-airflow}"
GENERATED="$DAGS_ROOT/dags/generated"

PYTHON="$REPO_ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON=python3
fi

"$PYTHON" "$SCRIPT_DIR/generate_dags.py" --tag "$TAG" --registry "$REGISTRY" --image-name "$IMAGE_NAME"

shopt -s nullglob
py_files=("$GENERATED"/*.py)
shopt -u nullglob
[[ ${#py_files[@]} -gt 0 ]] || { echo "ERROR: no generated DAG files in $GENERATED" >&2; exit 1; }

POD="$(kubectl get pod -n "$NAMESPACE" -l component=dag-processor -o jsonpath='{.items[0].metadata.name}')"

for py in "${py_files[@]}"; do
  name="$(basename "$py")"
  echo "Publishing $name to $POD..."
  kubectl cp "$py" "$NAMESPACE/$POD:/opt/airflow/dags/$name" -c dag-processor
done

echo "Published ${#py_files[@]} DAG file(s) using ${REGISTRY}/${IMAGE_NAME}:${TAG}."
