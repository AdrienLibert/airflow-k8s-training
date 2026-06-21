from lib.metrics.config import emit_result, load_config
from lib.metrics.pipeline import run_extract


def run() -> None:
    emit_result(run_extract(load_config()))
