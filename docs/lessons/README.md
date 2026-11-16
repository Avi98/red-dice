# Lessons — redis-event-loop

Learning curriculum for the Redis re-implementation in Python — from raw sockets
to a live, event-driven TCP server.

## Syllabus

- [Lesson 1 — Socket Programming: From File Descriptor to Listening Server](lesson-01-sockets.md)
- [Lesson 2 — The Event-Driven Accept Loop: From Raw `epoll` / `kqueue` to a Live Server](lesson-02-event-driven-accept-loop.md)

## Current module

**Module: Sockets & event-driven I/O.** Lesson 1 established the socket model and
non-blocking basics; Lesson 2 built the event-driven accept loop on raw
`epoll` / `kqueue` (no `selectors` module).

## Status

- [x] Lesson 1 — socket from fd → listening server
- [x] Lesson 2 — event-driven accept loop via raw epoll/kqueue
- [ ] Lesson 3 — client `recv()` / close handling → RESP2 parser

## Next up

Lesson 3: take the live accept loop from Lesson 2 and add client read/close handling,
then start the RESP2 protocol parser.

## How to submit work for review

Point the teacher agent at the relevant file(s) — e.g.
`src/redis_event_loop/server/async_tcp_server.py` — plus any test output or
reproduction steps. The teacher will grade against the lesson's rubric and log
recurring gaps in `gaps-and-mistakes.md`.
