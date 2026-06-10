IMAGE="${IMAGE:-hello-world-tasks:latest}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

docker build -t "$IMAGE" "$SCRIPT_DIR"

mapfile -t WORKERS < <(docker ps --format '{{.Names}}' | grep -E 'worker' || true)
if [[ ${#WORKERS[@]} -eq 0 ]]; then
  exit 1
fi

for node in "${WORKERS[@]}"; do
  docker save "$IMAGE" | docker exec -i "$node" ctr -n k8s.io images import -
done