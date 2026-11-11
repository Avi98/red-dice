# redis-event-loop

A Python implementation of Redis internals — built **solely for learning and teaching**.

This project re-creates the core pieces of [Redis](https://github.com/redis/redis)
(the open-source in-memory data store) from scratch in Python, with a focus on
understanding the systems concepts rather than competing with the original:
TCP servers, non-blocking I/O, event loops, and eventually the command
parsing / RESP protocol layer on top.

> **Not production software.** The real Redis is a heavily-optimized C codebase
> battle-tested for over a decade. This is a teaching codebase — it favors
> clarity over speed.

## Why?

Redis is one of the best codebases to learn network programming from. This
repository attempts the same journey in Python so each concept can be read,
poked, and rewritten without fighting C toolchains:

- How a TCP server accepts connections (`socket`, `bind`, `listen`, `accept`)
- Why non-blocking sockets + an event loop beat one-thread-per-connection
- What `kqueue` (macOS/BSD) and `epoll` (Linux) actually do
- How Redis serves thousands of clients on a single thread

## Getting started

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
# install dependencies (dev group included) + the project itself, editable
uv sync

# run the server
uv run redis
```

## Current status

- [x] Async TCP server skeleton (kqueue-based, macOS)
- [ ] Connection accept loop
- [ ] RESP2 protocol parser
- [ ] Command dispatch (GET / SET / DEL ...)
- [ ] In-memory data structures (SDS-like strings, dicts, expiry)
- [ ] Persistence snapshots
- [ ] Replication

## Best practices used

This project is as much about practicing a disciplined Python workflow as
about Redis itself:

| Tool | Purpose |
|------|---------|
| [`uv`](https://docs.astral.sh/uv/) | Fast, reproducible dependency management and builds (`uv.lock`, `uv sync`) |
| [`pytest`](https://docs.pytest.org/) | Testing framework — unit tests for parsers, protocol layers, and server behavior |
| [`ruff`](https://docs.astral.sh/ruff/) | Extremely fast linter + formatter (`E`, `F`, `I` rule sets, 88-col lines) |
| [`ty`](https://docs.astral.sh/ty/) | Type checker — static type checking with per-path rule overrides (e.g. relaxed rules for `src/legacy/**`) |

Conventions enforced in this repo:

- Full static typing (`from __future__` style annotations, `str \| None` unions, typed `main() -> None`)
- No unused imports / variables (`ruff F`), sorted imports (`ruff I`)
- Standard library first — no runtime dependencies at all
- Logging over `print` (see `RLogger`) — aside from the one entry-point banner
- Entry points declared in `pyproject.toml` (`[project.scripts]`), not hand-rolled scripts

## Development

```bash
# lint + format check
uv run ruff check .
uv run ruff format --check .

# type check
uv run ty check

# run tests
uv run pytest
```

## License

[MIT](LICENSE) — see the [Redis license](https://github.com/redis/redis/blob/unstable/COPYING)
for the original project this one learns from.
