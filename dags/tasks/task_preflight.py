from lib.metrics.config import emit_result, load_config
from lib.metrics.pipeline import run_preflight


def run() -> None:
    emit_result(run_preflight(load_config()))
