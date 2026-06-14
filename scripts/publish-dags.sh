#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
NAMESPACE="${NAMESPACE:-airflow}"

GENERATED="$REPO_ROOT/dags/dags/generated"
VERSIONS="$REPO_ROOT/dags/dags/definitions/versions"

[[ -f "$VERSIONS" ]] || { echo "ERROR: missing $VERSIONS" >&2; exit 1; }

python3 "$SCRIPT_DIR/generate_dags.py"

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
