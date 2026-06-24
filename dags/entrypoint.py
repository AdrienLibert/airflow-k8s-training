import importlib.util
import sys
from pathlib import Path

TASKS_DIR = Path(__file__).resolve().parent / "tasks"


def _safe_filename(raw: str) -> str:
    name = Path(raw).name
    if name != raw or not name.endswith(".py"):
        raise SystemExit(f"invalid module file: {raw!r} (expected a .py basename)")
    return name


def load_module(filename: str):
    path = TASKS_DIR / filename
    if not path.is_file():
        raise SystemExit(f"unknown module file: {filename} (expected {path})")
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"failed to load module file: {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit("usage: entrypoint.py <module.py> <function> [args...]")
    filename = _safe_filename(sys.argv[1])
    function_name = sys.argv[2]
    module = load_module(filename)
    try:
        task_fn = getattr(module, function_name)
    except AttributeError as exc:
        raise SystemExit(f"{filename} has no function {function_name!r}") from exc
    if not callable(task_fn):
        raise SystemExit(f"{filename}.{function_name} is not callable")
    task_fn(*sys.argv[3:])


if __name__ == "__main__":
    main()
