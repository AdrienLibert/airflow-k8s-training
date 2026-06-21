#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from dag_definitions import (
    DEFINITIONS_DIR,
    TEMPLATE_DIR,
    build_render_tasks,
    load_all_definitions,
    load_platform_defaults,
    load_task_registry,
    parse_start_date,
)


def render_dag(definition, *, image: str, env: Environment, registry: dict, defaults: dict) -> str:
    template = env.get_template("dag.py.j2")
    return template.render(
        dag_id=definition.dag_id,
        start_date=parse_start_date(definition.start_date),
        schedule=definition.schedule,
        catchup=definition.catchup,
        tags=list(definition.tags),
        tasks=build_render_tasks(
            definition,
            registry=registry,
            defaults=defaults,
            image=image,
        ),
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

    definitions = load_all_definitions(DEFINITIONS_DIR)
    if not definitions:
        print(f"ERROR: no YAML DAG definitions found in {DEFINITIONS_DIR}", file=sys.stderr)
        return 1

    registry = load_task_registry()
    defaults = load_platform_defaults()
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )

    for definition in definitions:
        output = output_dir / f"{definition.dag_id}.py"
        output.write_text(render_dag(definition, image=image, env=env, registry=registry, defaults=defaults))
        print(f"generated {output.name} ({image})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
