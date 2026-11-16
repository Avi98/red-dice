# Lesson 2 — The Event-Driven Accept Loop: From Raw `epoll` / `kqueue` to a Live Server

> **Project context:** this lesson maps directly to
> [`src/redis_event_loop/server/async_tcp_server.py`](../../src/redis_event_loop/server/async_tcp_server.py).
> Lesson 1 ended with a listening socket in non-blocking mode and named the missing
> piece: an **event loop** that waits for readiness and accepts. This lesson builds
> that loop using the OS-native readiness notifiers directly — **no `selectors` module**.

---

## 1. What the event loop adds

Lesson 1 got us to: `socket -> bind -> listen -> setblocking(False)`.

That is a *listening socket*, not yet a *server*. Without a loop, `start()` returns,
the process exits, the kernel closes the fd, and `nc -zv localhost 3001` gets
**Connection refused** — the exact gotcha Lesson 1 hit.

The missing piece is a loop that:

```
events = notifier.wait()     # sleeps here — zero CPU while idle
for event in events:
    if it's the listener: accept()      # new client arrived
    else:                  recv()/send() # existing client spoke
```

One thread watches all fds. When one is ready, act. Repeat. That is the whole
architecture of a high-performance single-threaded I/O server (Redis-style).

---

## 2. The notifier API from scratch (no `selectors`)

### 2.1 epoll (Linux)

```python
import select

event_buff = select.epoll()
event_buff.register(server.fileno(), select.EPOLLIN)   # EPOLLIN=1, EPOLLOUT=4, EPOLLERR=8
triggered_events = event_buff.poll(timeout=1000)      # -> [(fd, mask), ...]
event_buff.close()
```

Live-verified facts about the raw `select.epoll` API:

| Member | Behaviour |
|---|---|
| `register(fd, eventmask)` | ask the kernel to watch `fd` for `eventmask` |
| `poll(timeout=None, maxevents=-1)` | sleep until ready; returns `[(fd, mask), ...]` |
| `modify(fd, eventmask)` | change interest on an already-registered fd |
| `close()` | tear down the poller |
| `control` | **does not exist** on epoll — use `poll` |

Event shape: a list of **tuples** `(fd, mask)`. In our live check: `[(3, 1)]` where
`1 == EPOLLIN`.

### 2.2 kqueue (macOS / BSD)

```python
event_buff = select.kqueue()
event_k = select.kevent(
    server.fileno(),
    filter=select.KQ_FILTER_READ,
    flags=select.KQ_EV_ADD | select.KQ_EV_ENABLE,
)
triggered_events = event_buff.control([event_k], 10)   # -> [events]; ev.ident == fd
event_buff.close()
```

### 2.3 Why skip `selectors`

`selectors.DefaultSelector()` / `EpollSelector` / `KqueueSelector` wrap the raw
calls behind a friendlier `register/select/modify/close` surface. Fine for real
apps; the "from scratch" exercise wants the raw feel — and the bugs you'll hit
(e.g. `control` on epoll) only appear when you use the raw API yourself.

---

## 3. Worked example — epoll accept loop (from scratch)

```python
import select, socket

def start(host: str = "0.0.0.0", port: str = "8080") -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, int(port)))
    server.listen(5)
    server.setblocking(False)

    ep = select.epoll()
    ep.register(server.fileno(), select.EPOLLIN)

    while True:
        events = ep.poll(timeout=1000)
        for fd, mask in events:
            if fd == server.fileno():
                conn, addr = server.accept()
                conn.close()   # client connection handled / released

    ep.close()
    server.close()
```

Flow: create -> register -> **poll** -> unpack `(fd, mask)` -> check fd -> accept -> cleanup.

---

## 4. Worked example — kqueue accept loop (from scratch)

```python
import select

def start(host: str = "0.0.0.0", port: str = "8080") -> None:
    server = ...  # socket/bind/listen/setblocking(False) as above

    kq = select.kqueue()
    kev = select.kevent(
        server.fileno(),
        filter=select.KQ_FILTER_READ,
        flags=select.KQ_EV_ADD | select.KQ_EV_ENABLE,
    )
    triggered = kq.control([kev], 10)

    for ev in triggered:
        if ev.ident == server.fileno():
            conn, addr = server.accept()
            conn.close()

    kq.close()
    server.close()
```

Flow: create kqueue -> submit kevent -> **control** -> iterate events (`.ident`) -> accept -> cleanup.

---

## 5. Bridging to the project: diagnosing the missing loop in `async_tcp_server.py`

The skeleton already sketched the right shape. The missing/broken parts:

1. **Wrong notifier call for epoll.** The code branches on `hasattr(select, "kqueue")`
   / `hasattr(select, "epoll")`, then does `if hasattr(event_buff, "control"):`. For
   **epoll** that check is `False` -> falls to `else` -> `triggered_events` is never
   assigned -> the `for ev in triggered_events:` loop hits an unbound variable
   (`NameError`). Correct shape: epoll -> `poll`; kqueue -> `control`.

2. **Event-shape mismatch.** epoll yields `(fd, mask)` tuples; kqueue yields objects
   with `.ident`. `if ev.ident == server.fileno():` only fits kqueue.

3. **No loop.** Even with the right notifier call, the code handles one event then
   closes the server — no `while True` around the wait.

4. **Accepted connection never closed.** `conn, addr = server.accept()` — no `conn.close()`.

5. **`print` vs logger.** Repo convention: logging over print (see `RLogger`), except
   the one entry-point banner.

---

## 6. Where we are on the checklist

```
[x] Listener creation:  socket -> bind -> listen -> setblocking(False)
[x] SO_REUSEPORT set
[x] Register listener with kqueue/epoll          (Lesson 2)
[x] Event loop: wait -> accept -> register client (Lesson 2, accept half)
[ ] recv()/close handling for clients            (Lesson 3)
[ ] RESP2 protocol parser                        (Lesson 3)
[ ] Command dispatch (GET/SET/DEL ...)           (Lesson 4)
[ ] In-memory data structures                    (Lesson 5)
[ ] Persistence snapshots / replication        (later)
```

---

## 7. Exercises

1. **Live-verify the raw epoll path:** build the from-scratch epoll loop above and run a
   client against it. Confirm events arrive as `[(fd, mask), ...]`.
2. **Swap in kqueue code:** on macOS/BSD, run the kqueue version. Confirm events expose
   `.ident`.
3. **Break it deliberately:** remove the loop and re-run. Confirm the process exits
   immediately -> `nc` -> *Connection refused*.
4. **Bridge it:** wire the correct notifier call into `async_tcp_server.py` and get a
   live accept loop running.

---

## 8. Vocabulary recap

| Term | Meaning |
|---|---|
| event notifier | OS service that sleeps until fds are ready (`epoll`, `kqueue`) |
| readiness | the state that triggered an event (e.g. `EPOLLIN` / `KQ_FILTER_READ`) |
| level-triggered | keep re-reporting readiness until handled (default for epoll/kqueue) |
| edge-triggered | notify once per state change; must drain fully (later lesson) |

**Next lesson:** client `recv()` / close handling -> RESP2 parser (Lesson 3).
