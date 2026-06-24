from lib.hello import run as hello_run
from lib.message import run as message_run
from lib.world import run as world_run


def get_hello() -> None:
    hello_run()


def get_world() -> None:
    world_run()


def print_message(hello: str, world: str) -> None:
    message_run(hello, world)
