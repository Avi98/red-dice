import socket

from redis_event_loop.core.notifier import Notifier
from redis_event_loop.r_logger import RLogger

logging = RLogger("ASYNC_TCP_SERVER")

MAX_ACTIVE_CONNECTION = 63556


class AsyncTcpServer:
    def __init__(self) -> None: ...

    def start(self, host: str, port: int) -> None:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.setblocking(False)

        server.bind((host, port))
        server.listen(MAX_ACTIVE_CONNECTION)

        notify = Notifier()
        notify.init()

        notify_poll = notify.notifier

        while True:
            events = notify.get_events()

            for file_no, event in events:
                if file_no == server.fileno():
                    client_socket, addr = server.accept()
                    server.setblocking(False)

                    client_fd = client_socket.fileno()
