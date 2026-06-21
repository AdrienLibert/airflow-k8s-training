from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class MetricsConfig:
    events_source: Path
    output_root: Path
    interval_start: datetime

    @property
    def hour_key(self) -> str:
        return self.interval_start.astimezone(timezone.utc).strftime("%Y-%m-%dT%H")

    @property
    def work_dir(self) -> Path:
        return self.output_root / self.hour_key


def _parse_interval_start(raw: str) -> datetime:
    value = raw.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def load_config() -> MetricsConfig:
    events_source = Path(os.environ.get("EVENTS_SOURCE", "/app/fixtures/events/raw.jsonl"))
    output_root = Path(os.environ.get("METRICS_OUTPUT_DIR", "/tmp/metrics/hourly"))
    raw_interval = os.environ.get("DATA_INTERVAL_START", "2026-06-20T14:00:00+00:00")
    return MetricsConfig(
        events_source=events_source,
        output_root=output_root,
        interval_start=_parse_interval_start(raw_interval),
    )


def emit_result(payload: dict) -> None:
    print(json.dumps(payload, sort_keys=True))
