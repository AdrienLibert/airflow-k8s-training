
NAMESPACE="${NAMESPACE:-airflow}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

helm repo add apache-airflow https://airflow.apache.org 2>/dev/null || true
helm repo update

helm upgrade --install airflow apache-airflow/airflow \
  -n "$NAMESPACE" \
  --create-namespace \
  -f "$SCRIPT_DIR/values.yaml" \
  "$@"