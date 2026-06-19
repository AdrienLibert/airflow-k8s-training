#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

DAGS_ROOT = Path(__file__).resolve().parent.parent
DEFS = DAGS_ROOT / "definitions"
TEMPLATE_DIR = DAGS_ROOT / "templates"
IMAGE_PLACEHOLDER = re.compile(r"\{\{\s*image\s*\}\}")


def parse_start_date(raw: object) -> date:
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    if isinstance(raw, str):
        return date.fromisoformat(raw)
    raise ValueError(f"unsupported start_date value: {raw!r}")


def substitute_image(value: str, image: str) -> str:
    return IMAGE_PLACEHOLDER.sub(image, value)


def prepare_tasks(tasks: list[dict], image: str) -> list[dict]:
    prepared: list[dict] = []
    for task in tasks:
        item = dict(task)
        if "image" in item:
            item["image"] = substitute_image(str(item["image"]), image)
        prepared.append(item)
    return prepared


def render_dag(yaml_path: Path, image: str, env: Environment) -> str:
    payload = yaml.safe_load(yaml_path.read_text())
    if not isinstance(payload, dict) or len(payload) != 1:
        raise ValueError(f"{yaml_path.name} must contain exactly one top-level DAG key")

    dag_id, config = next(iter(payload.items()))
    default_args = config.get("default_args", {})
    template = env.get_template("dag.py.j2")
    return template.render(
        dag_id=dag_id,
        start_date=parse_start_date(default_args["start_date"]),
        schedule=config["schedule"],
        catchup=config.get("catchup", False),
        tags=config.get("tags", []),
        tasks=prepare_tasks(config["tasks"], image),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Airflow DAG Python files from YAML")
    parser.add_argument("--tag", required=True, help="Task image semver tag")
    parser.add_argument("--output-dir", required=True, type=Path, help="Temp output directory")
    parser.add_argument("--image-name", required=True)
    parser.add_argument(
        "--image",
        help="Full task image reference (overrides --image-name and --tag)",
    )
    return parser.parse_args()


def resolve_image(args: argparse.Namespace) -> str:
    if args.image:
        return args.image
    return f"{args.image_name}:{args.tag}"


def main() -> int:
    args = parse_args()
    image = resolve_image(args)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    yaml_files = sorted(DEFS.glob("*.yaml"))
    if not yaml_files:
        print(f"ERROR: no YAML DAG definitions found in {DEFS}", file=sys.stderr)
        return 1

    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )

    for yaml_path in yaml_files:
        dag_id = yaml_path.stem
        output = output_dir / f"{dag_id}.py"
        output.write_text(render_dag(yaml_path, image, env))
        print(f"generated {output.name} ({image})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
