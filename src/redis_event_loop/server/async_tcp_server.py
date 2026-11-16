from redis_event_loop.r_logger import RLogger

logging = RLogger("ASYNC_TCP_SERVER")


class AsyncTcpServer:
    def __init__(self) -> None:
        pass

    def start(self, host: str, port: int): ...
