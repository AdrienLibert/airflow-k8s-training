from lib.metrics.config import emit_result, load_config
from lib.metrics.pipeline import run_notify_summary


def run() -> None:
    emit_result(run_notify_summary(load_config()))
