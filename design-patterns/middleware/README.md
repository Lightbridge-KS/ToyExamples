# Middleware: Chain of Responsibility, Decorator, Proxy (toy example)

*Four requests pass through logging, an auth check and a cache before reaching an endpoint.
The same scenario is written twice: as the GoF book draws it (58 lines of code, 7 classes)
and in modern Python (57 lines, 2 classes, both plain data). The two files produce the same
transcript.*

```sh
# from this folder
uv run classic.py     # the GoF shape
uv run modern.py      # the modern shape
uv run compare.py     # proof: both transcripts are identical
```

Read the two side by side: `code --diff classic.py modern.py`, or select both in VS Code's
Explorer and choose **Compare Selected**. UML for both shapes is in
[ARCHITECTURE.md](ARCHITECTURE.md).

## The idea

**Three intents, one shape.** Decorator, Chain of Responsibility and Proxy are all "something
with the handler's interface that holds a handler". They differ only in what they do with
the call:

```
request ──► logged ──► require_user ──► cached_by_path ──► report
              │              │                 │
              │              │                 └─ Proxy: calls report only on a cache miss
              │              └─ Chain of Responsibility: no user? answer 401 and stop here
              └─ Decorator: always passes on, adds a log line on the way back
```

GoF give the held handler three names (`component`, `successor`, `subject`), which hides the
fact that it is one field. Once a handler is a function, each wrapper becomes a
`Handler -> Handler` function. That is exactly what Python's `@decorator` syntax applies:

```
CLASSIC                                               MODERN
───────                                               ──────
class AuthHandler(Handler):                           def require_user(next_handler: Handler) -> Handler:
    __init__(successor): self._successor = ...            @wraps(next_handler)
    handle(req): ... self._successor.handle(req)          def handler(req): ... next_handler(req)
                                                          return handler

LoggingDecorator(AuthHandler(CachingProxy(e)), out)   stack(report, partial(logged, out=out),
                                                            require_user, cached_by_path)
```

The modern file is not shorter (57 lines against 58). What changes is the *kind* of thing
each part is. The wrappers become functions, the endpoint becomes a function, and the stack
becomes a list you read in request order.

## Classic → modern

| Pattern | Classic (`classic.py`) | Modern (`modern.py`) | What does the work instead |
|---|---|---|---|
| **Decorator** | `LoggingDecorator(Handler)` holds `_component` and adds a log line | `logged(next_handler, *, out)` returns a wrapping closure | `@decorator`, closures, `functools.wraps` |
| **Chain of Responsibility** | `AuthHandler(Handler)` holds `_successor`; returns 401 or delegates | `require_user(next_handler)`: returns 401 or calls on | the same, plus `reduce()` to build the chain |
| **Proxy** | `CachingProxy(Handler)` holds `_subject` and a `_cache` dict | `cached_by_path(next_handler)`; the cache lives in the closure | closures; `functools.cache` ready-made |

## Why it works

- **One shape, one name.** In `modern.py` every wrapper's inner handler is `next_handler`.
  The three patterns look the same in code because structurally they *are* the same. What
  separates them is the line that does or skips the call.
- **The stack is data.** `stack(report, a, b, c)` reads in the order a request travels.
  Moving a layer means moving an item in a list, not re-nesting constructor calls from the
  inside out.
- **The language already has the operator.** Stacking `@partial(logged, out=out)`,
  `@require_user` and `@cached_by_path` on `def report` builds the same app as `stack()`
  (verified). Python applies decorators bottom-up, so the one listed last ends up innermost.
- **The stdlib ships ready-made proxies.** `functools.cache` is a caching proxy, and
  `inspect.unwrap(app)` follows the `__wrapped__` links that `@wraps` leaves, down to `report`
  (verified).

## The price

- **Order is behaviour, and nothing checks it.** This is true of both shapes. Every layer has
  type `Handler -> Handler`, so the type checker accepts any order. Put the cache outside the
  auth check and the anonymous request gets `200 contents of /report`: alice's protected
  response, served from cache (verified; exercise 1).
- **`@wraps` makes the stack look like the endpoint.** `app.__name__` is `"report"`, even
  though `app` is the logging wrapper. That's right for introspection, but confusing when you
  want to know which layer you're holding. In `classic.py`, `app` is plainly a
  `LoggingDecorator`.
- **Closure state is hidden.** You can't inspect or clear the `cache` dict inside
  `cached_by_path` from outside. The classic `proxy._cache` can be reached, and
  `functools.cache` adds `cache_info()` / `cache_clear()` for this reason.
- **Configuration adds a level.** `logged` needs `out`, which means either a third nested
  function or `partial`, the trick from [training-loop](../training-loop/README.md).

## When the classic still wins

- **Wrapping a whole object, not one call.** A proxy for something with `get` / `put` /
  `delete`, or for a remote object, has to forward many methods. That needs a class, or a
  `__getattr__` that forwards every attribute. `weakref.proxy` in the stdlib and
  `wrapt.ObjectProxy` work this way.
- **Several hooks per layer.** Django's class-based middleware can also define
  `process_view()` and `process_exception()`. Once a layer joins in at several points, a
  class groups those methods under one name.

## Variants worth naming

- **`(request, call_next)` middleware.** Starlette's `dispatch(request, call_next)`, Express's
  `(req, res, next)` and Koa's `(ctx, next)` receive `next` on each call, not at wrapping
  time. That removes one level of nesting and works the same way.
- **`functools.cache` as the proxy.** It keys on the whole request, so here alice and bob each
  get their own entry (verified). That's safer than `cached_by_path`, which shares one entry
  per path the way a CDN would. It needs hashable arguments, which is one reason `Request`
  is `frozen=True`.
- **Virtual proxy.** `functools.cached_property` creates an expensive attribute the first
  time it is read: a proxy for something that doesn't exist yet.

## Where you meet it

- Django middleware: the documented function form takes `get_response` and returns a
  `middleware(request)` closure. That is `Handler -> Handler`, exactly as in this toy.
- WSGI / ASGI: `app = SomeMiddleware(app)`. These are classes wrapping a callable app, so the
  classic shape is alive here.
- Flask-Login's `@login_required`: one Chain of Responsibility link, written as a decorator.
- `functools.cache`, `lru_cache`, `tenacity.retry`: Proxy and Decorator from a library.

## Exercises

1. **Reorder.** Build `stack(report, partial(logged, out=out), cached_by_path, require_user)`
   and run it. What does the anonymous request get, and did any tool warn you? Then make the
   app safe in *any* order by changing what the cache uses as its key.
2. **Rate limit.** Add `rate_limit(max_per_user)`, which returns `429` once a user has made
   too many requests, to both files. It needs configuration *and* state. How many nested
   functions does the modern version need, and does `partial` still help?
3. **Use the stdlib proxy.** Replace `cached_by_path` with `functools.cache`. How many times
   does the endpoint run now, and why does `Request` have to be `frozen=True`?
4. **Decorate at definition time.** Rewrite the modern `run()` with `@` decorators stacked on
   `report`. Which one ends up outermost, and how does that line up with `stack()`'s
   argument order?
