REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE_DIR="${REPO_ROOT}/config/profiles"

DEPLOY_PROFILE="${DEPLOY_PROFILE:-local}"

case "$DEPLOY_PROFILE" in
  local | gcp) ;;
  *)
    echo "ERROR: DEPLOY_PROFILE must be 'local' or 'gcp' (got '${DEPLOY_PROFILE}')" >&2
    exit 1
    ;;
esac

_load_profile_file() {
  local file="$1"
  if [[ -f "$file" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "$file"
    set +a
  fi
}

_load_profile_file "${PROFILE_DIR}/${DEPLOY_PROFILE}.env"

GCP_REGION="${GCP_REGION:-us-central1}"
IMAGE_NAME="${IMAGE_NAME:-airflow-k8s-tasks}"
PLATFORM_IMAGE_NAME="${PLATFORM_IMAGE_NAME:-airflow}"
LOCAL_PLATFORM_REPOSITORY="${LOCAL_PLATFORM_REPOSITORY:-local/airflow}"

if [[ -z "${REGISTRY:-}" && -n "${GCP_PROJECT:-}" ]]; then
  REGISTRY="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/airflow"
fi

should_push_images() {
  if [[ "${PUSH_IMAGES:-}" == "true" ]]; then
    return 0
  fi
  if [[ "${PUSH_IMAGES:-}" == "false" ]]; then
    return 1
  fi
  [[ "$DEPLOY_PROFILE" == "gcp" ]]
}

_gcp_config_hint() {
  echo "Set GCP_PROJECT in ${PROFILE_DIR}/gcp.env" >&2
}

_registry_image_ref() {
  local name="$1"
  local tag="$2"
  if [[ "$DEPLOY_PROFILE" == "local" ]]; then
    echo "${name}:${tag}"
    return
  fi
  if [[ -z "${REGISTRY:-}" ]]; then
    echo "ERROR: GCP profile requires GCP_PROJECT or REGISTRY." >&2
    _gcp_config_hint
    exit 1
  fi
  echo "${REGISTRY}/${name}:${tag}"
}

task_image_ref() {
  _registry_image_ref "$IMAGE_NAME" "$1"
}

platform_image_ref() {
  if [[ "$DEPLOY_PROFILE" == "local" ]]; then
    echo "${LOCAL_PLATFORM_REPOSITORY}:${1}"
    return
  fi
  _registry_image_ref "$PLATFORM_IMAGE_NAME" "$1"
}

platform_image_repository() {
  if [[ "$DEPLOY_PROFILE" == "local" ]]; then
    echo "$LOCAL_PLATFORM_REPOSITORY"
    return
  fi
  if [[ -z "${REGISTRY:-}" ]]; then
    echo "ERROR: GCP profile requires GCP_PROJECT or REGISTRY." >&2
    _gcp_config_hint
    exit 1
  fi
  echo "${REGISTRY}/${PLATFORM_IMAGE_NAME}"
}
