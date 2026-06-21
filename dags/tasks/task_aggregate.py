from lib.metrics.config import emit_result, load_config
from lib.metrics.pipeline import _parse_upstream, run_aggregate


def run(upstream_json: str = "") -> None:
    upstream = _parse_upstream(upstream_json) if upstream_json else None
    emit_result(run_aggregate(load_config(), upstream))
