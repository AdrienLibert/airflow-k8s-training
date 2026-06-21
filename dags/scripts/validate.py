#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

import jsonschema
import yaml

from check_policy import collect_policy_errors
from dag_definitions import DEFINITIONS_DIR, SCHEMA_PATH, load_all_definitions


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


def _normalize_for_schema(value: object) -> object:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _normalize_for_schema(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_for_schema(item) for item in value]
    return value


def _validate_schema(definitions_dir: Path, schema: dict) -> list[str]:
    paths = sorted(definitions_dir.glob("*.yaml"))
    if not paths:
        return [f"no YAML DAG definitions found in {definitions_dir}"]

    errors: list[str] = []
    validator = jsonschema.Draft202012Validator(schema)
    for path in paths:
        payload = _normalize_for_schema(yaml.safe_load(path.read_text()))
        for error in sorted(validator.iter_errors(payload), key=lambda item: list(item.path)):
            location = ".".join(str(part) for part in error.path) or "<root>"
            errors.append(f"{path.name}: {location}: {error.message}")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate DAG definitions (schema + policy)")
    parser.add_argument(
        "--definitions-dir",
        type=Path,
        default=DEFINITIONS_DIR,
        help="Directory containing author YAML definitions",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    failed = False

    schema_errors = _validate_schema(args.definitions_dir, _load_schema())
    if schema_errors:
        failed = True
        for error in schema_errors:
            print(f"schema: {error}", file=sys.stderr)
    else:
        count = len(list(args.definitions_dir.glob("*.yaml")))
        print(f"schema: ok ({count} definition(s))")

    policy_errors = collect_policy_errors(definitions_dir=args.definitions_dir)
    if policy_errors:
        failed = True
        for error in policy_errors:
            print(f"policy: {error}", file=sys.stderr)
    else:
        count = len(load_all_definitions(args.definitions_dir))
        print(f"policy: ok ({count} definition(s))")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
