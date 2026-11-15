import os

from redis_event_loop.server.async_tcp_server import AsyncTcpServer


def main() -> None:
    print("Hello from redis-event-loop!")
    server = AsyncTcpServer()

    server.start(
        os.environ.get("HOST", "localhost"),
        os.environ.get("PORT", "3001"),
    )


if __name__ == "__main__":
    main()
