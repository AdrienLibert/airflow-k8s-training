from lib.metrics.config import emit_result, load_config
from lib.metrics.pipeline import (
    _parse_upstream,
    run_aggregate,
    run_extract,
    run_normalize,
    run_notify_summary,
    run_preflight,
    run_verify,
    run_write_summary,
)


def preflight() -> None:
    emit_result(run_preflight(load_config()))


def extract_hourly() -> None:
    emit_result(run_extract(load_config()))


def normalize(upstream_json: str = "") -> None:
    upstream = _parse_upstream(upstream_json) if upstream_json else None
    emit_result(run_normalize(load_config(), upstream))


def aggregate(upstream_json: str = "") -> None:
    upstream = _parse_upstream(upstream_json) if upstream_json else None
    emit_result(run_aggregate(load_config(), upstream))


def write_summary(upstream_json: str = "") -> None:
    upstream = _parse_upstream(upstream_json) if upstream_json else None
    emit_result(run_write_summary(load_config(), upstream))


def verify(upstream_json: str = "") -> None:
    upstream = _parse_upstream(upstream_json) if upstream_json else None
    emit_result(run_verify(load_config(), upstream))


def notify_summary(upstream_json: str = "") -> None:
    upstream = _parse_upstream(upstream_json) if upstream_json else None
    emit_result(run_notify_summary(load_config(), upstream))
