from lib.metrics.config import emit_result, load_config
from lib.metrics.pipeline import run_verify


def run() -> None:
    emit_result(run_verify(load_config()))
