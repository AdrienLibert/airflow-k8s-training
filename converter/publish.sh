#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 --codebase-tag <semver> [--codebase-image <name>] [--converter-tag <tag>]" >&2
  exit 1
}

CODEBASE_TAG=""
CODEBASE_IMAGE="${CODEBASE_IMAGE:-hello-world-tasks}"
CONVERTER_TAG="${CONVERTER_TAG:-latest}"
CONVERTER_IMAGE="${CONVERTER_IMAGE:-hello-world-converter}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --codebase-tag)
      [[ $# -ge 2 ]] || usage
      CODEBASE_TAG="$2"
      shift 2
      ;;
    --codebase-image)
      [[ $# -ge 2 ]] || usage
      CODEBASE_IMAGE="$2"
      shift 2
      ;;
    --converter-tag)
      [[ $# -ge 2 ]] || usage
      CONVERTER_TAG="$2"
      shift 2
      ;;
    *)
      usage
      ;;
  esac
done

[[ -n "$CODEBASE_TAG" ]] || usage

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFINITIONS="$REPO_ROOT/dags/definitions"
NAMESPACE="${NAMESPACE:-airflow}"

GENERATED="$(mktemp -d)"
cleanup() { rm -rf "$GENERATED"; }
trap cleanup EXIT

docker run --rm \
  -v "$DEFINITIONS:/defs:ro" \
  -v "$GENERATED:/out" \
  "${CONVERTER_IMAGE}:${CONVERTER_TAG}" \
  python generate_dags.py \
    --definitions /defs \
    --output-dir /out \
    --tag "$CODEBASE_TAG" \
    --image-name "$CODEBASE_IMAGE"

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

echo "Published ${#py_files[@]} DAG file(s) using ${CODEBASE_IMAGE}:${CODEBASE_TAG}."
