REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$ENV_FILE"
  set +a
fi

GCP_REGION="${GCP_REGION:-us-central1}"
IMAGE_NAME="${IMAGE_NAME:-airflow-k8s-tasks}"
PLATFORM_IMAGE_NAME="${PLATFORM_IMAGE_NAME:-airflow}"

if [[ -z "${REGISTRY:-}" && -n "${GCP_PROJECT:-}" ]]; then
  REGISTRY="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/airflow"
fi

_registry_image_ref() {
  local name="$1"
  local tag="$2"
  if [[ -z "${REGISTRY:-}" ]]; then
    echo "ERROR: set GCP_PROJECT or REGISTRY in ${ENV_FILE} (see .env.example)" >&2
    exit 1
  fi
  echo "${REGISTRY}/${name}:${tag}"
}

task_image_ref() {
  _registry_image_ref "$IMAGE_NAME" "$1"
}

platform_image_ref() {
  _registry_image_ref "$PLATFORM_IMAGE_NAME" "$1"
}
