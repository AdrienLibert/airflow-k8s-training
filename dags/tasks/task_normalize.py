from lib.metrics.config import emit_result, load_config
from lib.metrics.pipeline import run_normalize


def run() -> None:
    emit_result(run_normalize(load_config()))
