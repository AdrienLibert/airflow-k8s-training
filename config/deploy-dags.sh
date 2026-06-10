
REPO="$(cd "$(dirname "$0")/../dags" && pwd)"
REL="${1#./}"

case "$REL" in
  dags/*) DEST="/opt/airflow/dags/${REL#dags/}" ;;
  lib/*)  DEST="/opt/airflow/dags/lib/${REL#lib/}" ;;
  *) echo "Usage: $0 dags/... or lib/..." >&2; exit 1 ;;
esac

POD=$(kubectl get pod -n airflow -l component=dag-processor -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n airflow "$POD" -c dag-processor -- mkdir -p "$(dirname "$DEST")"
kubectl cp "$REPO/$REL" "airflow/$POD:$DEST" -c dag-processor
