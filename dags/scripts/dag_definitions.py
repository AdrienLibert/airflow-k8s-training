from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import yaml

DAGS_ROOT = Path(__file__).resolve().parent.parent
DEFINITIONS_DIR = DAGS_ROOT / "definitions"
PLATFORM_DIR = DAGS_ROOT / "platform"
TASKS_DIR = DAGS_ROOT / "tasks"
TEMPLATE_DIR = DAGS_ROOT / "templates"
SCHEMA_PATH = DAGS_ROOT / "schemas" / "dag-definition.schema.json"


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    module: str
    dependencies: tuple[str, ...]


@dataclass(frozen=True)
class DagDefinition:
    dag_id: str
    path: Path
    schedule: str
    start_date: str
    catchup: bool
    tags: tuple[str, ...]
    tasks: tuple[TaskSpec, ...]


def load_yaml(path: Path) -> object:
    return yaml.safe_load(path.read_text())


def load_platform_defaults() -> dict:
    path = PLATFORM_DIR / "defaults.yaml"
    payload = load_yaml(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a mapping")
    return payload


def load_task_registry() -> dict[str, dict]:
    path = PLATFORM_DIR / "tasks.yaml"
    payload = load_yaml(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a mapping")
    tasks = payload.get("tasks")
    if not isinstance(tasks, dict):
        raise ValueError(f"{path} must define tasks mapping")
    return {str(task_id): dict(spec) for task_id, spec in tasks.items() if isinstance(spec, dict)}


def parse_definition_file(path: Path) -> DagDefinition:
    payload = load_yaml(path)
    if not isinstance(payload, dict) or len(payload) != 1:
        raise ValueError(f"{path.name} must contain exactly one top-level DAG key")

    dag_id, config = next(iter(payload.items()))
    if not isinstance(config, dict):
        raise ValueError(f"{path.name}: DAG config must be a mapping")

    raw_tasks = config.get("tasks")
    if not isinstance(raw_tasks, list) or not raw_tasks:
        raise ValueError(f"{path.name}: tasks must be a non-empty list")

    tasks: list[TaskSpec] = []
    for index, raw_task in enumerate(raw_tasks):
        if not isinstance(raw_task, dict):
            raise ValueError(f"{path.name}: tasks[{index}] must be a mapping")
        task_id = raw_task.get("task_id")
        if not isinstance(task_id, str):
            raise ValueError(f"{path.name}: tasks[{index}].task_id must be a string")
        module = raw_task.get("module")
        if not isinstance(module, str):
            raise ValueError(f"{path.name}: tasks[{index}].module must be a string")
        raw_deps = raw_task.get("dependencies", [])
        if not isinstance(raw_deps, list):
            raise ValueError(f"{path.name}: tasks[{index}].dependencies must be a list")
        dependencies = tuple(str(dep) for dep in raw_deps)
        tasks.append(TaskSpec(task_id=task_id, module=module, dependencies=dependencies))

    raw_tags = config.get("tags", [])
    if not isinstance(raw_tags, list):
        raise ValueError(f"{path.name}: tags must be a list")

    schedule = config.get("schedule")
    if not isinstance(schedule, str):
        raise ValueError(f"{path.name}: schedule must be a string")

    return DagDefinition(
        dag_id=str(dag_id),
        path=path,
        schedule=schedule,
        start_date=_coerce_start_date(config.get("start_date"), path.name),
        catchup=bool(config.get("catchup", False)),
        tags=tuple(str(tag) for tag in raw_tags),
        tasks=tuple(tasks),
    )


def _coerce_start_date(raw: object, source: str) -> str:
    if isinstance(raw, datetime):
        return raw.date().isoformat()
    if isinstance(raw, date):
        return raw.isoformat()
    if isinstance(raw, str):
        return raw
    raise ValueError(f"{source}: start_date must be a date string")


def load_all_definitions(definitions_dir: Path = DEFINITIONS_DIR) -> list[DagDefinition]:
    paths = sorted(definitions_dir.glob("*.yaml"))
    return [parse_definition_file(path) for path in paths]


def parse_start_date(raw: str) -> date:
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    return date.fromisoformat(raw)


def build_render_tasks(
    definition: DagDefinition,
    *,
    registry: dict[str, dict],
    defaults: dict,
    image: str,
) -> list[dict]:
    operator_defaults = defaults.get("operator")
    if not isinstance(operator_defaults, dict):
        raise ValueError("platform/defaults.yaml must define operator mapping")

    prepared: list[dict] = []
    for task in definition.tasks:
        if task.task_id not in registry:
            raise ValueError(f"unknown task_id in generator: {task.task_id}")

        entry = registry[task.task_id]
        item: dict = {
            "task_id": task.task_id,
            "namespace": operator_defaults["namespace"],
            "image": image,
            "image_pull_policy": operator_defaults["image_pull_policy"],
            "cmds": ["python", "entrypoint.py", f"{task.module}.py", task.task_id],
            "get_logs": operator_defaults["get_logs"],
            "is_delete_operator_pod": operator_defaults["is_delete_operator_pod"],
            "in_cluster": operator_defaults["in_cluster"],
        }
        if "do_xcom_push" in entry:
            item["do_xcom_push"] = entry["do_xcom_push"]
        if "arguments" in entry:
            item["arguments"] = entry["arguments"]
        if "env_vars" in entry:
            item["env_vars"] = entry["env_vars"]
        if task.dependencies:
            item["dependencies"] = list(task.dependencies)
        prepared.append(item)
    return prepared
