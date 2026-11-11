from server.async_tcp_server import AsyncTcpServer


def main() -> None:
    print("Hello from redis-event-loop!")
    server = AsyncTcpServer()

    server.start("localhost", "3001")


if __name__ == "__main__":
    main()
