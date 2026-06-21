from lib.metrics.config import emit_result, load_config
from lib.metrics.pipeline import run_write_summary


def run() -> None:
    emit_result(run_write_summary(load_config()))
