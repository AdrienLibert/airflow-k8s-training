from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from lib.metrics.config import MetricsConfig, emit_result


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n")


def _event_in_hour(ts_raw: str, config: MetricsConfig) -> bool:
    ts = ts_raw.replace("Z", "+00:00")
    event_time = datetime.fromisoformat(ts)
    if event_time.tzinfo is None:
        event_time = event_time.replace(tzinfo=timezone.utc)
    event_hour = event_time.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    run_hour = config.interval_start.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    return event_hour == run_hour


def _parse_upstream(raw: str | None) -> dict | None:
    if not raw:
        return None
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise SystemExit("upstream payload must be a JSON object")
    return payload


def run_preflight(config: MetricsConfig) -> dict:
    if not config.events_source.is_file():
        raise SystemExit(f"events source missing: {config.events_source}")
    return {
        "events_source": str(config.events_source),
        "hour_key": config.hour_key,
    }


def run_extract(config: MetricsConfig) -> dict:
    rows = [row for row in _read_jsonl(config.events_source) if _event_in_hour(row["ts"], config)]
    if config.work_dir is not None:
        config.work_dir.mkdir(parents=True, exist_ok=True)
        _write_jsonl(config.work_dir / "extracted.jsonl", rows)
    return {"hour_key": config.hour_key, "extracted_count": len(rows), "rows": rows}


def run_normalize(config: MetricsConfig, upstream: dict | None = None) -> dict:
    if upstream is None:
        if config.work_dir is None:
            raise SystemExit("normalize requires upstream payload or METRICS_OUTPUT_DIR for local runs")
        upstream = {"rows": _read_jsonl(config.work_dir / "extracted.jsonl")}
    rows = upstream["rows"]
    seen: set[str] = set()
    normalized: list[dict] = []
    for row in rows:
        event_id = str(row["event_id"])
        if event_id in seen:
            continue
        seen.add(event_id)
        normalized.append(
            {
                "event_id": event_id,
                "route": str(row["route"]),
                "status": str(row["status"]),
                "latency_ms": int(row["latency_ms"]),
            }
        )
    return {
        "hour_key": config.hour_key,
        "input_count": len(rows),
        "normalized_count": len(normalized),
        "rows": normalized,
    }


def run_aggregate(config: MetricsConfig, upstream: dict | None = None) -> dict:
    if upstream is None:
        if config.work_dir is None:
            raise SystemExit("aggregate requires upstream payload or METRICS_OUTPUT_DIR for local runs")
        upstream = {"rows": _read_jsonl(config.work_dir / "normalized.jsonl")}
    rows = upstream["rows"]
    buckets: dict[tuple[str, str], dict] = {}
    for row in rows:
        key = (row["route"], row["status"])
        bucket = buckets.setdefault(
            key,
            {"route": row["route"], "status": row["status"], "count": 0, "latency_ms_total": 0},
        )
        bucket["count"] += 1
        bucket["latency_ms_total"] += row["latency_ms"]
    groups = []
    total_events = 0
    for bucket in sorted(buckets.values(), key=lambda item: (item["route"], item["status"])):
        count = bucket["count"]
        total_events += count
        groups.append(
            {
                "route": bucket["route"],
                "status": bucket["status"],
                "count": count,
                "avg_latency_ms": round(bucket["latency_ms_total"] / count, 2),
            }
        )
    summary = {
        "hour_key": config.hour_key,
        "total_events": total_events,
        "groups": groups,
    }
    return summary


def run_write_summary(config: MetricsConfig, upstream: dict | None = None) -> dict:
    if upstream is None:
        upstream = json.loads((config.work_dir / "summary.json").read_text())
    return {
        "hour_key": upstream["hour_key"],
        "total_events": upstream["total_events"],
        "groups": upstream["groups"],
        "status": "written",
    }


def run_verify(config: MetricsConfig, upstream: dict | None = None) -> dict:
    if upstream is None:
        upstream = json.loads((config.work_dir / "manifest.json").read_text())
    failures: list[str] = []
    if upstream.get("total_events", 0) == 0:
        failures.append("no events in hour window")
    if not upstream.get("groups"):
        failures.append("summary has no groups")
    status = "ok" if not failures else "failed"
    result = {
        "hour_key": upstream.get("hour_key", config.hour_key),
        "status": status,
        "failures": failures,
        "total_events": upstream.get("total_events", 0),
        "groups": upstream.get("groups", []),
    }
    if failures:
        raise SystemExit(json.dumps(result, sort_keys=True))
    return result


def run_notify_summary(config: MetricsConfig, upstream: dict | None = None) -> dict:
    if upstream is None:
        upstream = json.loads((config.work_dir / "summary.json").read_text())
    return {
        "hour_key": upstream.get("hour_key", config.hour_key),
        "status": "ok",
        "total_events": upstream.get("total_events", 0),
        "groups": upstream.get("groups", []),
    }
