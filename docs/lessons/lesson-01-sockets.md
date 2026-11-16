# Lesson 1 — Socket Programming: From File Descriptor to Listening Server

> **Project context:** this lesson maps directly to
> [`src/redis_event_loop/server/async_tcp_server.py`](../../src/redis_event_loop/server/async_tcp_server.py).
> Read them side by side — every claim here is something the code already does (or is about to do).

---

## 1. What a socket actually is
**
A **socket is a file descriptor** — a plain **integer the OS hands you — that represents
one endpoint of a network connection. This is the single most important idea in all
of network programming:

```
open("/tmp/data.txt")  ->  fd 7   (file)
socket(AF_INET, ...)   ->  fd 9   (network endpoint)
```

Both are "files" to the kernel. You read from them, write to them, and close them
with the same syscalls. Even the event notifiers we'll meet later (`kqueue`, `epoll`)
are fds themselves — that's why `select.kqueue()` has a `fromfd()` method.

**Consequence:** anything that works on files (non-blocking mode, readiness
polling, `close()`) works on sockets. The whole Unix design composes.

### The two kinds of TCP sockets

| | Listening socket | Connection socket |
|---|---|---|
| Created by | `socket()` + `bind()` + `listen()` | `accept()` (per client) |
| Carries data | **Never** | Yes — this is where bytes flow |
| Lifetime | One per server | One per client |
| Analogy | The receptionist's desk | The private meeting room |

A listening socket never sees a single byte of client data. Its only job is to
accept handshakes and produce new connection sockets.

---

## 2. The four-step server dance

Every TCP server ever written does these four steps. Our code already does 1–3:

```python
# 1. Create an fd (AF_INET = IPv4, SOCK_STREAM = TCP)
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# 2. Claim an address + port ("0.0.0.0" = all local interfaces)
server.bind(("0.0.0.0", 3001))

# 3. Mark it as a listener; argument is the *backlog*
server.listen(65535)

# 4. Pop one completed connection off the backlog queue  ← NOT YET WRITTEN
conn, addr = server.accept()
```

### What each step really does in the kernel

- **`socket()`** — asks the kernel for a new fd. Nothing is attached to the network yet.
- **`bind()`** — records "this port is mine" in the kernel's port table. This is why
  a second process binding the same port gets `EADDRINUSE` (see `SO_REUSEPORT` below).
- **`listen()`** — converts the socket into a listener and creates the **backlog**:
  a queue of connections that finished the TCP 3-way handshake while nobody called
  `accept()` yet. If the queue fills, new handshakes are refused/dropped.
- **`accept()`** — pops one entry from that queue and returns a *brand-new socket*
  dedicated to that client, plus its address.

> **Lesson 1 gotcha we hit in real life:** running `nc -zv localhost 8080` against
> this project gives *Connection refused* — the OS found nobody bound to the port.
> Three stacked reasons: (a) our default port is **3001**, not 8080; (b) the server
> wasn't running; and (c) even if it were, `start()` returned immediately, the
> process exited, and the kernel closed the socket. **A port is only "open" for as
> long as a live process holds it.** A server must sit in a loop to keep listening.

### `SO_REUSEPORT` — the line we set and why

```python
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
```

Normally the kernel forbids two sockets on the same port. `SO_REUSEPORT` allows
several *processes* to bind the exact same `host:port`, and the kernel
load-balances incoming connections across them. Real servers use this to scale
horizontally on one machine — N identical worker processes, one port, zero proxy
in front. Redis-style trick: it's how you get multi-core parallelism without a
load balancer.

---

## 3. Blocking vs non-blocking — the "why" of this whole project

### Default (blocking) mode

By default every socket call **sleeps** until it has an answer:

| Call | Sleeps until |
|---|---|
| `accept()` | some client connects |
| `recv()` | data arrives |
| `send()` | the kernel's send buffer has room |
| `connect()` | the handshake completes |

A naive server handles this with **one thread per connection**:

```
thread per client -> each thread frozen in recv(), doing nothing
10,000 clients    -> 10,000 threads -> GBs of stack + constant context switching
```

That's the "one-thread-per-connection" trap the README calls out.

### Non-blocking mode — what `setblocking(False)` changes

```python
server.setblocking(False)
```

The contract flips from "wait nicely" to "answer instantly, even if the answer is
*not yet*":

| Call | Blocking mode | Non-blocking mode |
|---|---|---|
| `accept()` | sleeps until a client comes | returns **now**: a connection, or raises `BlockingIOError` |
| `recv()` | sleeps until data comes | returns **now**: bytes, `b""` (peer closed), or `BlockingIOError` |
| `send()` | sleeps until buffer has room | sends what fits, or raises `BlockingIOError` |

`BlockingIOError` is **not an error in the "something broke" sense** — it's the OS
saying *"I would have to block you; try again later."* A huge fraction of event-loop
bugs come from people treating it as fatal. Our loop must catch it and move on.

### The new problem non-blocking creates

If nothing ever blocks, your loop spins at 100% CPU calling `accept()`/`recv()`
just to be told "not yet" ten million times a second. Which raises the real question:

> **How do I know when it's actually *worth* calling `accept()` or `recv()`?**

---

## 4. Event notifiers: `kqueue` and `epoll`

That question is answered by the OS's **event notification APIs**. They answer one
question efficiently:

> *"Here are 10,000 fds. Sleep until **any** of them are ready, then tell me which."*

One thread watches every socket in the server. This is precisely how real Redis
serves tens of thousands of clients on a single thread. The generic loop:

```
events = notifier.wait()          # sleeps here — zero CPU while idle
for event in events:
    if it's the listener:  accept()        # new client arrived
    else:                  recv()/send()  # existing client spoke
```

Our code picks the OS-native API at runtime:

```python
if hasattr(select, "kqueue"):        # macOS / BSD
    event_buff = select.kqueue()
elif hasattr(select, "epoll"):       # Linux
    event_buff = select.epoll()
```

Same code runs natively on the laptop **and** inside the Linux Docker container.

### The two APIs are *not* interchangeable

| | `kqueue` (macOS/BSD) | `epoll` (Linux) |
|---|---|---|
| Register an fd | submit a `select.kevent(fd, KQ_FILTER_READ, KQ_EV_ADD)` **changelist** to `control()` | `register(fd, select.EPOLLIN)` |
| Wait for events | `control(None, max_events, timeout)` — `max_events` must be > 0 | `poll(timeout)` returns `[(fd, mask), ...]` |
| "Modify" call | n/a — resubmit changelist | `control()` with **no args** = modify registrations |
| EOF signal | event carries `KQ_EV_EOF` flag | recv() returning `b""` |

> **The conflation bug we already stepped on:** `event_buff.control()` with no
> arguments works for *epoll* (its "modify" mode) but **crashes on kqueue**, which
> requires `(changelist, max_events, timeout)`. Also, `kqueue.control()` with
> `max_events=0` is not a valid "apply changes" call — the registration has to be
> submitted alongside an actual wait. Lesson: these APIs look similar but their
> argument shapes differ; pick one, learn it properly, then port.

### Level-triggered vs edge-triggered (a preview)

Both `kqueue` and default-`epoll` are **level-triggered**: as long as data is
sitting unread on a socket, the notifier keeps reporting it every cycle. If you
don't drain all data, you'll simply be re-notified next loop — safe and
beginner-friendly. (Edge-triggered mode notifies you *once* per state change and
requires draining everything; a later lesson.)

---

## 5. Where we are on the checklist

```
[x] Listener creation:  socket -> bind -> listen -> setblocking(False)
[x] SO_REUSEPORT set
[ ] Register listener with kqueue/epoll          (Lesson 2)
[ ] Event loop: wait -> accept -> register client (Lesson 2)
[ ] recv()/close handling for clients            (Lesson 2)
[ ] RESP2 protocol parser                        (Lesson 3)
[ ] Command dispatch (GET/SET/DEL ...)           (Lesson 4)
[ ] In-memory data structures                    (Lesson 5)
```

The missing piece is the **event loop** — without it the process exits immediately
and `nc` gets *Connection refused* (see §2).

---

## 6. Exercises

1. **Prove "a port is only open while a process lives":** run
   `uv run redis` in one terminal and `lsof -nP -iTCP:3001 -sTCP:LISTEN` in
   another. Ctrl-C the server and run `lsof` again — the listener is gone.
2. **Backlog by hand:** temporarily set `listen(1)`, then hammer the port with
   several rapid `nc -zv localhost 3001` connections before any `accept()` runs.
   Observe refusals once the backlog queue fills.
3. **Break it deliberately:** comment out `server.setblocking(False)` and try to
   build the accept loop anyway. Watch `accept()` freeze the whole process — this
   is *the* motivation for non-blocking I/O.
4. **Read the real thing:** find `anetListen` and `serverAccept` in the
   [Redis C source](https://github.com/redis/redis/blob/unstable/src/anet.c) and
   match each line to a step from §2.

---

## 7. Vocabulary recap

| Term | Meaning |
|---|---|
| fd / file descriptor | integer handle to a kernel object (file, socket, notifier…) |
| bind | claim `ip:port` in the kernel's port table |
| listen / backlog | become a listener; queue of pre-accepted connections |
| accept | pop a completed connection; returns a per-client socket |
| blocking / non-blocking | sleep until ready / return immediately with `BlockingIOError` |
| `BlockingIOError` | "would block" — retry later, **not** a failure |
| readiness / event notifier | OS service that sleeps until fds are ready (`kqueue`, `epoll`) |
| level-triggered | keep re-reporting readiness until the app handles it |
| `SO_REUSEPORT` | multiple processes may bind the same port; kernel load-balances |

**Next lesson:** registering the listener with kqueue/epoll and writing the
`wait -> accept -> recv` loop that keeps this process alive.
