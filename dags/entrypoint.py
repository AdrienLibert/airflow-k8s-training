import importlib.util
import sys
from pathlib import Path

TASKS_DIR = Path(__file__).resolve().parent / "tasks"


def load_task(task_name: str):
    path = TASKS_DIR / f"task_{task_name}.py"
    if not path.is_file():
        raise SystemExit(f"unknown task: {task_name} (expected {path})")
    spec = importlib.util.spec_from_file_location(f"task_{task_name}", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"failed to load task: {task_name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: entrypoint.py <task_name> [args...]")
    task_name = sys.argv[1]
    module = load_task(task_name)
    if not hasattr(module, "run"):
        raise SystemExit(f"task_{task_name}.py must define run()")
    module.run(*sys.argv[2:])


if __name__ == "__main__":
    main()
