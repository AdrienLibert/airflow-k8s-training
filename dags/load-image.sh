SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VERSIONS="$SCRIPT_DIR/dags/definitions/versions"

[[ -f "$VERSIONS" ]] || { echo "ERROR: missing $VERSIONS" >&2; exit 1; }

mapfile -t WORKERS < <(docker ps --format '{{.Names}}' | grep -E 'worker' || true)
[[ ${#WORKERS[@]} -gt 0 ]] || { echo "ERROR: no k8s worker containers found" >&2; exit 1; }

declare -A BUILT
while IFS= read -r line || [[ -n "$line" ]]; do
  [[ "$line" =~ ^[[:space:]]*# ]] && continue
  [[ -z "${line// /}" ]] && continue
  [[ "$line" == *"="* ]] || continue

  dag="${line%%=*}"
  version="${line#*=}"
  dag="$(echo "$dag" | tr -d ' \n\r')"
  version="$(echo "$version" | tr -d ' \n\r')"

  [[ "$version" != "latest" ]] || { echo "ERROR: latest not allowed for $dag" >&2; exit 1; }
  [[ -n "${BUILT[$version]:-}" ]] && continue

  image="hello-world-tasks:${version}"
  docker build -t "$image" "$SCRIPT_DIR"
  for node in "${WORKERS[@]}"; do
    docker save "$image" | docker exec -i "$node" ctr -n k8s.io images import -
  done
  BUILT[$version]=1
  echo "built and loaded $image ($dag)"
done < "$VERSIONS"
