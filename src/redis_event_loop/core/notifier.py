import select
from abc import ABC


class NotifierAbc(ABC):
    def __init__(self) -> None:
        self.poll: select.epoll | select.kqueue | None = None

    def register(
        self,
    ) -> select.epoll | select.kqueue:
        pass

    def get_events(
        self,
    ) -> list[tuple[int, int]]:  # type:ignore
        pass

    @property
    def notifier(
        self,
    ):
        return self.poll


class Notifier(NotifierAbc):
    def init(
        self,
    ) -> None:
        if hasattr(select.select, "epoll"):
            self.poll = select.epoll()
        self.poll = select.kqueue()  # type:ignore

    def get_events(
        self,
    ) -> list[tuple[int, int]]:
        if self.poll is not None and hasattr(self.poll, "poll"):
            return self.poll.poll(timeout=1.0)
        return self.poll.control(None, 64, None)  # type:ignore
