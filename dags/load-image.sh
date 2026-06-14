#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
IMAGES="$SCRIPT_DIR/dags/definitions/images"

[[ -f "$IMAGES" ]] || { echo "ERROR: missing $IMAGES" >&2; exit 1; }

mapfile -t WORKERS < <(
  docker ps --format '{{.Names}}' | grep -E '^(desktop-(worker|control-plane)|kind-(worker|control-plane))' || true
)
[[ ${#WORKERS[@]} -gt 0 ]] || { echo "ERROR: no local k8s nodes found" >&2; exit 1; }

declare -A BUILT
while IFS= read -r line || [[ -n "$line" ]]; do
  [[ "$line" =~ ^[[:space:]]*# ]] && continue
  [[ -z "${line// /}" ]] && continue
  [[ "$line" == *"="* ]] || continue

  dag="${line%%=*}"
  tag="${line#*=}"
  dag="$(echo "$dag" | tr -d ' \n\r')"
  tag="$(echo "$tag" | tr -d ' \n\r')"

  [[ "$tag" != "latest" ]] || { echo "ERROR: latest not allowed for $dag" >&2; exit 1; }
  [[ -n "${BUILT[$tag]:-}" ]] && continue

  image="hello-world-tasks:${tag}"
  docker build -t "$image" "$SCRIPT_DIR"
  for node in "${WORKERS[@]}"; do
    docker save "$image" | docker exec -i "$node" ctr -n k8s.io images import -
  done
  BUILT[$tag]=1
  echo "built and loaded $image ($dag)"
done < "$IMAGES"
