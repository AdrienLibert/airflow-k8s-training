#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DAGS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$DAGS_ROOT/.." && pwd)"
NAMESPACE="${NAMESPACE:-airflow}"

GENERATED="$DAGS_ROOT/dags/generated"
IMAGES="$DAGS_ROOT/dags/definitions/images"

[[ -f "$IMAGES" ]] || { echo "ERROR: missing $IMAGES" >&2; exit 1; }

PYTHON="$REPO_ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON=python3
fi

"$PYTHON" "$SCRIPT_DIR/generate_dags.py"

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

echo "Published ${#py_files[@]} DAG file(s)."
