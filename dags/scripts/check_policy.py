#!/usr/bin/env python3
from __future__ import annotations

import ast
import sys
from pathlib import Path

from dag_definitions import (
    DEFINITIONS_DIR,
    TASKS_DIR,
    DagDefinition,
    load_all_definitions,
    load_platform_defaults,
    load_task_registry,
)


def _check_filename_matches_dag_id(defn: DagDefinition) -> list[str]:
    if defn.path.stem != defn.dag_id:
        return [f"{defn.path.name}: top-level key {defn.dag_id!r} must match filename stem {defn.path.stem!r}"]
    return []


def _check_tasks_registered(defn: DagDefinition, registry: set[str]) -> list[str]:
    errors: list[str] = []
    for task in defn.tasks:
        if task.task_id not in registry:
            errors.append(f"{defn.path.name}: unknown task_id {task.task_id!r} (not in platform/tasks.yaml)")
    return errors


def _module_functions(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    return {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }


def _check_task_modules(defn: DagDefinition) -> list[str]:
    errors: list[str] = []
    for task in defn.tasks:
        path = TASKS_DIR / f"{task.module}.py"
        if not path.is_file():
            errors.append(
                f"{defn.path.name}: missing module file {path.relative_to(TASKS_DIR.parent)} "
                f"for task {task.task_id!r}"
            )
            continue
        try:
            functions = _module_functions(path)
        except SyntaxError as exc:
            errors.append(f"{defn.path.name}: invalid Python in module {task.module!r}: {exc}")
            continue
        if task.task_id not in functions:
            errors.append(
                f"{defn.path.name}: module {task.module!r} has no function {task.task_id!r}"
            )
    return errors


def _check_unique_task_ids(defn: DagDefinition) -> list[str]:
    seen: set[str] = set()
    errors: list[str] = []
    for task in defn.tasks:
        if task.task_id in seen:
            errors.append(f"{defn.path.name}: duplicate task_id {task.task_id!r}")
        seen.add(task.task_id)
    return errors


def _check_dependencies(defn: DagDefinition) -> list[str]:
    task_ids = {task.task_id for task in defn.tasks}
    errors: list[str] = []
    for task in defn.tasks:
        for dep in task.dependencies:
            if dep not in task_ids:
                errors.append(
                    f"{defn.path.name}: task {task.task_id!r} depends on unknown task {dep!r}"
                )
            if dep == task.task_id:
                errors.append(f"{defn.path.name}: task {task.task_id!r} cannot depend on itself")
    return errors


def _check_cycles(defn: DagDefinition) -> list[str]:
    graph = {task.task_id: set(task.dependencies) for task in defn.tasks}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> str | None:
        if node in visiting:
            return node
        if node in visited:
            return None
        visiting.add(node)
        for dep in graph.get(node, set()):
            if cycle := visit(dep):
                return cycle
        visiting.remove(node)
        visited.add(node)
        return None

    for task_id in graph:
        if task_id not in visited:
            if visit(task_id):
                return [f"{defn.path.name}: dependency cycle detected among tasks"]
    return []


def _check_limits(defn: DagDefinition, defaults: dict) -> list[str]:
    limits = defaults.get("limits")
    if not isinstance(limits, dict):
        return ["platform/defaults.yaml must define limits mapping"]

    errors: list[str] = []
    max_tasks = limits.get("max_tasks_per_dag")
    if isinstance(max_tasks, int) and len(defn.tasks) > max_tasks:
        errors.append(
            f"{defn.path.name}: too many tasks ({len(defn.tasks)} > {max_tasks})"
        )

    max_tags = limits.get("max_tags")
    if isinstance(max_tags, int) and len(defn.tags) > max_tags:
        errors.append(
            f"{defn.path.name}: too many tags ({len(defn.tags)} > {max_tags})"
        )
    return errors


def collect_policy_errors(
    definitions: list[DagDefinition] | None = None,
    *,
    definitions_dir: Path = DEFINITIONS_DIR,
) -> list[str]:
    if definitions is None:
        definitions = load_all_definitions(definitions_dir)

    if not definitions:
        return [f"no YAML DAG definitions found in {definitions_dir}"]

    registry = load_task_registry()
    defaults = load_platform_defaults()
    registry_ids = set(registry)

    errors: list[str] = []
    for defn in definitions:
        errors.extend(_check_filename_matches_dag_id(defn))
        errors.extend(_check_tasks_registered(defn, registry_ids))
        errors.extend(_check_task_modules(defn))
        errors.extend(_check_unique_task_ids(defn))
        errors.extend(_check_dependencies(defn))
        errors.extend(_check_cycles(defn))
        errors.extend(_check_limits(defn, defaults))
    return errors


def main() -> int:
    errors = collect_policy_errors()
    if errors:
        for error in errors:
            print(f"policy: {error}", file=sys.stderr)
        return 1
    print(f"policy: ok ({len(load_all_definitions())} definition(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
