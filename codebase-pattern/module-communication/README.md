# Module communication: public APIs, orchestration, and pub/sub

A modular monolith in miniature, with two versions of checkout. Both reuse the
same Inventory, Orders, and Notifications modules. Everything runs in one process
using stdlib Python.

```sh
# From this folder
uv run python -m checkout_toy.demo
uv run python -m checkout_toy.event_demo
```

The original demo uses direct API calls. The event demo publishes `OrderPlaced`
to a synchronous event bus, first with a notification subscriber, then with an
added audit subscriber. Both demos check their outcomes through public APIs.

## Read the code in this order

1. `checkout_toy/checkout.py` — the entire cross-module workflow, in three calls.
2. Each business package's `__init__.py` — the public names available to callers.
3. Each `_impl.py` — the state and rules hidden behind those names.
4. `checkout_toy/demo.py` — instance wiring and observable outcomes.

```text
demo (wires instances)
  └── Checkout.place_order()
        ├── Inventory.reserve()                  -> None or exception
        ├── Orders.create()                      -> OrderReceipt
        └── Notifications.send_confirmation()    -> None
```

Checkout imports the public packages. The three business packages never import
one another. An immutable receipt carries data across a boundary; the private order
list stays inside Orders. The orchestrator owns the sequence; each module owns its
own rules and state. The composition root chooses instances; it does not execute
the workflow's individual steps.

`__all__` documents exports and affects star imports. Underscores signal privacy;
Python does **not** prevent importing `_impl` or accessing `_stock`. Real boundary
enforcement requires additional tooling. This toy has no transaction or rollback:
a failure after reservation can leave partial effects.

## Walkthrough and exercises

`walkthrough.qmd` contains runtime and dependency diagrams, a comparison with
direct peer calls and pub/sub, limitations, and exercises. It is source for the
rich-document viewer; the Python files are the runnable implementation.

## The pub/sub version

Read `event_bus.py`, `orders/events.py`, `event_checkout.py`, then `event_demo.py`.

```text
EventCheckout.place_order()
  ├── Inventory.reserve()
  ├── Orders.create() -> OrderReceipt
  └── EventBus.publish(OrderPlaced(...))
        ├── subscription adapter -> Notifications.send_confirmation()
        └── subscription adapter -> Audit.record()
```

`event_demo.py` owns the subscriptions. EventCheckout knows the event contract and
bus, without importing Notifications or Audit. Adapters translate the event into
each subscriber module's existing public call. Adding Audit changes the wiring;
the publisher stays the same. The event contract is owned by Orders, and Checkout
publishes it after reservation and order creation; `Orders.create()` alone does not
publish events.

This bus is one typed channel (`EventBus[OrderPlaced]`), with no routing among event
types. `subscribe()` records callbacks; `publish()` calls all of them inline in
registration order. New subscribers receive future publications, with no replay.
Publishing without subscribers does nothing beyond printing the trace.

The event demo also shows rejection before publication and a failing subscriber.
The first handler exception stops delivery to later handlers and propagates to
Checkout, even though stock is reserved and the order exists. There are no
background workers, retries, persistence, rollback, or delivery guarantees.
