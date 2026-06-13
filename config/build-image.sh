SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REGISTRY="${REGISTRY:-local}"
TAG="${TAG:-3.2.2-dagfactory}"
IMAGE="${REGISTRY}/airflow:${TAG}"

docker build -t "$IMAGE" "$SCRIPT_DIR"

if [[ "${1:-}" == "--push" ]]; then
  docker push "$IMAGE"
fi
