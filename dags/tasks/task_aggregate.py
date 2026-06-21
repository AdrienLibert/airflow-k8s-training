from lib.metrics.config import emit_result, load_config
from lib.metrics.pipeline import run_aggregate


def run() -> None:
    emit_result(run_aggregate(load_config()))
