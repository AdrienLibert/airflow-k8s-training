import airflow
from airflow.sdk import dag  # noqa: F401
from dagfactory import load_yaml_dags
from pathlib import Path

_DAGS = Path(__file__).resolve().parent

load_yaml_dags(
    globals_dict=globals(),
    dags_folder=str(_DAGS / "definitions"),
)
