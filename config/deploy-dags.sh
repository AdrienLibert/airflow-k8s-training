REPO="$(cd "$(dirname "$0")/../dags" && pwd)"
DEFS="$REPO/dags/definitions"
VERSIONS="$DEFS/versions"

[[ -f "$VERSIONS" ]] || { echo "ERROR: missing $VERSIONS" >&2; exit 1; }

get_version() {
  local dag="$1" line version
  line="$(grep -E "^[[:space:]]*${dag}[[:space:]]*=" "$VERSIONS" | head -1)" || true
  [[ -n "$line" ]] || { echo "ERROR: no version for $dag in $VERSIONS" >&2; return 1; }
  version="$(echo "${line#*=}" | tr -d ' \n\r')"
  echo "$version"
}

POD=$(kubectl get pod -n airflow -l component=dag-processor -o jsonpath='{.items[0].metadata.name}')

for yaml in "$DEFS"/*.yaml; do
  [[ -f "$yaml" ]] || continue
  dag="$(basename "$yaml" .yaml)"
  version="$(get_version "$dag")"
  [[ "$version" != "latest" ]] || { echo "ERROR: latest not allowed for $dag" >&2; exit 1; }

  tmp="$(mktemp)"
  sed "s/{{ version }}/${version}/g" "$yaml" > "$tmp"
  dest="/opt/airflow/dags/definitions/${dag}.yaml"

  kubectl exec -n airflow "$POD" -c dag-processor -- mkdir -p "$(dirname "$dest")"
  kubectl cp "$tmp" "airflow/$POD:$dest" -c dag-processor
  rm -f "$tmp"
done

kubectl cp "$REPO/dags/loader.py" "airflow/$POD:/opt/airflow/dags/loader.py" -c dag-processor
