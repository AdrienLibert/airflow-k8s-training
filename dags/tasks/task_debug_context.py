import os
import sys


def run(*args: str) -> None:
    print("=== argv ===")
    for i, value in enumerate(sys.argv):
        print(f"  argv[{i}]={value!r}")

    print("=== extra args (from entrypoint) ===")
    for i, value in enumerate(args):
        print(f"  arg[{i}]={value!r}")

    print("=== AIRFLOW_* env ===")
    for key in sorted(os.environ):
        if key.startswith("AIRFLOW_"):
            print(f"  {key}={os.environ[key]!r}")

    print("=== all env ===")
    for key in sorted(os.environ):
        print(f"  {key}={os.environ[key]!r}")
