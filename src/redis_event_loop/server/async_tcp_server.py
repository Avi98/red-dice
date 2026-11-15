import select
import socket

from redis_event_loop.r_logger import RLogger

logging = RLogger("ASYNC_TCP_SERVER")


class AsyncTcpServer:
    def __init__(self) -> None:
        pass

    def start(self, host: str, port: str) -> None:

        server = self._create_listener(host, port)
        conn, addr = server.accept()

        # kqueue on macOS/BSD, epoll on Linux — picked at runtime so the
        # same code runs natively and inside a Linux container.
        if hasattr(select, "kqueue"):
            event_buff = select.kqueue()
            event_k = select.kevent(
                server.fileno(),
                filter=select.KQ_FILTER_READ,
                flags=select.KQ_EV_ADD | select.KQ_EV_ENABLE,
            )

        elif hasattr(select, "epoll"):
            event_buff = select.epoll()
        else:
            msg = "no event notification API available (kqueue/epoll)"
            raise RuntimeError(msg)

        logging.info(f"{event_buff.fromfd}")

        if hasattr(event_buff, "control"):
            event_buff.control([event_k], 0)

        else:
            # event_buff.
            pass

    def _create_listener(
        self, host: str = "0.0.0.0", port: str = "8080"
    ) -> socket.socket:
        logging.info(f"Started TCP server {host=} and {port=}")

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        server.bind((host, int(port)))

        server.listen(65535)

        server.setblocking(False)

        return server
