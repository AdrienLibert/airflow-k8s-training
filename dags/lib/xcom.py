from __future__ import annotations

import json
from pathlib import Path

XCOM_FILE = Path("/airflow/xcom/return.json")


def push_xcom(value: object) -> None:
    if not XCOM_FILE.parent.is_dir():
        return
    XCOM_FILE.write_text(json.dumps(value, sort_keys=True))
