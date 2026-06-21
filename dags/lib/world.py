def run() -> None:
    from lib.xcom import push_xcom

    message = "World"
    print(message)
    push_xcom(message)
