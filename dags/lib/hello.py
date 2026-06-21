def run() -> None:
    from lib.xcom import push_xcom

    message = "Hello"
    print(message)
    push_xcom(message)
