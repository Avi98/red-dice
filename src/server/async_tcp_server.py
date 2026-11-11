import select
import socket

from r_logger import RLogger

logging = RLogger("ASYNC_TCP_SERVER")


class AsyncTcpServer:
    def __init__(self) -> None:
        pass

    def start(self, host: str, port: str) -> None:

        event_buff = select.kqueue()
        logging.info(f"{event_buff=}")

    def _server(self, host: str | None = "0.0.0.0", port: str | None = "8080") -> None:
        logging.info(f"Started TCP server {host=} and {port=}")

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        server.bind((host, port))

        server.listen(65535)

        server.setblocking(False)
