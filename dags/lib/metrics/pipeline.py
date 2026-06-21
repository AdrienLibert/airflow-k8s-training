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


def run_preflight(config: MetricsConfig) -> dict:
    if not config.events_source.is_file():
        raise SystemExit(f"events source missing: {config.events_source}")
    config.output_root.mkdir(parents=True, exist_ok=True)
    return {
        "events_source": str(config.events_source),
        "output_root": str(config.output_root),
        "hour_key": config.hour_key,
    }


def run_extract(config: MetricsConfig) -> dict:
    rows = [row for row in _read_jsonl(config.events_source) if _event_in_hour(row["ts"], config)]
    work_dir = config.work_dir
    work_dir.mkdir(parents=True, exist_ok=True)
    extracted_path = work_dir / "extracted.jsonl"
    _write_jsonl(extracted_path, rows)
    return {"hour_key": config.hour_key, "extracted_count": len(rows), "path": str(extracted_path)}


def run_normalize(config: MetricsConfig) -> dict:
    extracted_path = config.work_dir / "extracted.jsonl"
    rows = _read_jsonl(extracted_path)
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
    normalized_path = config.work_dir / "normalized.jsonl"
    _write_jsonl(normalized_path, normalized)
    return {
        "hour_key": config.hour_key,
        "input_count": len(rows),
        "normalized_count": len(normalized),
        "path": str(normalized_path),
    }


def run_aggregate(config: MetricsConfig) -> dict:
    normalized_path = config.work_dir / "normalized.jsonl"
    rows = _read_jsonl(normalized_path)
    buckets: dict[tuple[str, str], dict] = {}
    for row in rows:
        key = (row["route"], row["status"])
        bucket = buckets.setdefault(key, {"route": row["route"], "status": row["status"], "count": 0, "latency_ms_total": 0})
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
    summary_path = config.work_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")
    return {"hour_key": config.hour_key, "total_events": total_events, "groups": len(groups), "path": str(summary_path)}


def run_write_summary(config: MetricsConfig) -> dict:
    summary_path = config.work_dir / "summary.json"
    summary = json.loads(summary_path.read_text())
    manifest = {
        "hour_key": config.hour_key,
        "summary_path": str(summary_path),
        "total_events": summary["total_events"],
        "groups": summary["groups"],
    }
    manifest_path = config.work_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    return {"hour_key": config.hour_key, "manifest_path": str(manifest_path)}


def run_verify(config: MetricsConfig) -> dict:
    manifest = json.loads((config.work_dir / "manifest.json").read_text())
    summary = json.loads((config.work_dir / "summary.json").read_text())
    normalized_count = len(_read_jsonl(config.work_dir / "normalized.jsonl"))
    failures: list[str] = []
    if manifest["total_events"] != summary["total_events"]:
        failures.append("manifest total_events mismatch")
    if summary["total_events"] != normalized_count:
        failures.append("summary total_events != normalized row count")
    if summary["total_events"] == 0:
        failures.append("no events in hour window")
    status = "ok" if not failures else "failed"
    result = {"hour_key": config.hour_key, "status": status, "failures": failures}
    if failures:
        raise SystemExit(json.dumps(result, sort_keys=True))
    return result


def run_notify_summary(config: MetricsConfig) -> dict:
    summary = json.loads((config.work_dir / "summary.json").read_text())
    return {"hour_key": config.hour_key, "status": "ok", "total_events": summary["total_events"], "groups": summary["groups"]}
