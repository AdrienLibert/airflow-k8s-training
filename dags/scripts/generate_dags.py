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
IMAGES = DEFS / "images"
TEMPLATE_DIR = DAGS_ROOT / "dags" / "templates"
OUTPUT_DIR = DAGS_ROOT / "dags" / "generated"
IMAGE_TAG_PLACEHOLDER = re.compile(r"\{\{\s*image_tag\s*\}\}")


def load_image_tags(path: Path) -> dict[str, str]:
    image_tags: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or "=" not in line:
            continue
        dag, tag = (part.strip() for part in line.split("=", 1))
        if tag == "latest":
            raise ValueError(f"latest not allowed for {dag}")
        image_tags[dag] = tag
    return image_tags


def parse_start_date(raw: object) -> date:
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    if isinstance(raw, str):
        return date.fromisoformat(raw)
    raise ValueError(f"unsupported start_date value: {raw!r}")


def substitute_image_tag(value: str, tag: str) -> str:
    return IMAGE_TAG_PLACEHOLDER.sub(tag, value)


def prepare_tasks(tasks: list[dict], image_tag: str) -> list[dict]:
    prepared: list[dict] = []
    for task in tasks:
        item = dict(task)
        if "image" in item:
            item["image"] = substitute_image_tag(str(item["image"]), image_tag)
        prepared.append(item)
    return prepared


def render_dag(yaml_path: Path, image_tags: dict[str, str], env: Environment) -> str:
    payload = yaml.safe_load(yaml_path.read_text())
    if not isinstance(payload, dict) or len(payload) != 1:
        raise ValueError(f"{yaml_path.name} must contain exactly one top-level DAG key")

    dag_id, config = next(iter(payload.items()))
    if dag_id not in image_tags:
        raise ValueError(f"no image tag for {dag_id} in {IMAGES}")

    default_args = config.get("default_args", {})
    template = env.get_template("dag.py.j2")
    return template.render(
        dag_id=dag_id,
        start_date=parse_start_date(default_args["start_date"]),
        schedule=config["schedule"],
        catchup=config.get("catchup", False),
        tags=config.get("tags", []),
        tasks=prepare_tasks(config["tasks"], image_tags[dag_id]),
    )


def main() -> int:
    if not IMAGES.is_file():
        print(f"ERROR: missing {IMAGES}", file=sys.stderr)
        return 1

    yaml_files = sorted(DEFS.glob("*.yaml"))
    if not yaml_files:
        print(f"ERROR: no YAML DAG definitions found in {DEFS}", file=sys.stderr)
        return 1

    image_tags = load_image_tags(IMAGES)
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
        output.write_text(render_dag(yaml_path, image_tags, env))
        print(f"generated {output.relative_to(REPO_ROOT)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
