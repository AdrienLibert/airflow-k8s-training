NAMESPACE="${NAMESPACE:-airflow}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=registry.sh
source "$SCRIPT_DIR/registry.sh"

helm repo add apache-airflow https://airflow.apache.org 2>/dev/null || true
helm repo update

helm_args=(
  upgrade --install airflow apache-airflow/airflow
  -n "$NAMESPACE"
  --create-namespace
  -f "$SCRIPT_DIR/values.yaml"
  --timeout 25m
  --wait
)

if [[ "$DEPLOY_PROFILE" == "gcp" ]]; then
  TAG="${AIRFLOW_TAG:-3.2.2}"
  REPOSITORY="$(platform_image_repository)"
  helm_args+=(
    -f "$SCRIPT_DIR/values-gcp.yaml"
    --set "images.airflow.repository=${REPOSITORY}"
    --set "images.airflow.tag=${TAG}"
  )
fi

helm "${helm_args[@]}" "$@"
