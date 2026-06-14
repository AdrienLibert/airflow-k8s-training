#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from datetime import date, datetime
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

DAGS_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = DAGS_ROOT.parent
DEFS = DAGS_ROOT / "dags" / "definitions"
VERSIONS = DEFS / "versions"
TEMPLATE_DIR = DAGS_ROOT / "dags" / "templates"
OUTPUT_DIR = DAGS_ROOT / "dags" / "generated"
VERSION_PLACEHOLDER = re.compile(r"\{\{\s*version\s*\}\}")


def load_versions(path: Path) -> dict[str, str]:
    versions: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or "=" not in line:
            continue
        dag, version = (part.strip() for part in line.split("=", 1))
        if version == "latest":
            raise ValueError(f"latest not allowed for {dag}")
        versions[dag] = version
    return versions


def parse_start_date(raw: object) -> date:
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    if isinstance(raw, str):
        return date.fromisoformat(raw)
    raise ValueError(f"unsupported start_date value: {raw!r}")


def substitute_version(value: str, version: str) -> str:
    return VERSION_PLACEHOLDER.sub(version, value)


def prepare_tasks(tasks: list[dict], version: str) -> list[dict]:
    prepared: list[dict] = []
    for task in tasks:
        item = dict(task)
        if "image" in item:
            item["image"] = substitute_version(str(item["image"]), version)
        prepared.append(item)
    return prepared


def render_dag(yaml_path: Path, versions: dict[str, str], env: Environment) -> str:
    payload = yaml.safe_load(yaml_path.read_text())
    if not isinstance(payload, dict) or len(payload) != 1:
        raise ValueError(f"{yaml_path.name} must contain exactly one top-level DAG key")

    dag_id, config = next(iter(payload.items()))
    if dag_id not in versions:
        raise ValueError(f"no version for {dag_id} in {VERSIONS}")

    default_args = config.get("default_args", {})
    template = env.get_template("dag.py.j2")
    return template.render(
        dag_id=dag_id,
        start_date=parse_start_date(default_args["start_date"]),
        schedule=config["schedule"],
        catchup=config.get("catchup", False),
        tags=config.get("tags", []),
        tasks=prepare_tasks(config["tasks"], versions[dag_id]),
    )


def main() -> int:
    if not VERSIONS.is_file():
        print(f"ERROR: missing {VERSIONS}", file=sys.stderr)
        return 1

    yaml_files = sorted(DEFS.glob("*.yaml"))
    if not yaml_files:
        print(f"ERROR: no YAML DAG definitions found in {DEFS}", file=sys.stderr)
        return 1

    versions = load_versions(VERSIONS)
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for stale in OUTPUT_DIR.glob("*.py"):
        stale.unlink()

    for yaml_path in yaml_files:
        dag_id = yaml_path.stem
        output = OUTPUT_DIR / f"{dag_id}.py"
        output.write_text(render_dag(yaml_path, versions, env))
        print(f"generated {output.relative_to(REPO_ROOT)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
