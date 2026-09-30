# Hub-and-spoke (toy example)

*A smart-home hub and its devices, in ~90 lines of stdlib Python.*

```sh
uv run hub_and_spoke.py
```

## The idea

Every **spoke** talks only to the **hub**. Nothing else. The hub therefore becomes the
single home for three jobs that would otherwise be scattered across N devices:

| Job | Where it lives | In the code |
|---|---|---|
| Address book — who exists | hub | `Hub.spokes`, filled by `register()` |
| Desired state — what should be true | hub | `Hub.scenes` |
| Routing — who reacts to what | hub | `Hub.routes`, applied in `on_event()` |

A spoke keeps one reference (`self.hub`) and two verbs: `apply()` (obey) and `report()`
(emit). It cannot address a sibling because it has no handle to one. **The isolation is
structural, not a rule someone has to remember.**

```
                    ┌─────────────┐
        apply ─────►│             │◄───── report
   ┌────────┐       │     HUB     │       ┌────────┐
   │ light  │◄──────┤  registry   ├──────►│ sensor │
   └────────┘       │  scenes     │       └────────┘
                    │  routes     │
   ┌────────┐       │             │       ┌────────────┐
   │ blinds │◄──────┤             ├──────►│ thermostat │
   └────────┘       └─────────────┘       └────────────┘

   spoke ──✗── spoke        (no edge exists; there is nothing to call)
```

## Three flows the demo shows

1. **Fan-out** (hub → spokes): one `apply_scene("movie")` becomes three `apply()` calls.
   The hub initiates; spokes reconcile and return a receipt.
2. **Fan-in + route** (spoke → hub → spoke): the sensor reports `motion`; the hub looks up
   the route and tells the light to turn on. The sensor never knew a light existed.
3. **Unknown event**: the hub, not the spoke, decides an event has no consumer.

## Why the star wins as N grows

Every device wired to every other device is a **mesh**: N(N−1)/2 links, and every device
must carry an address book. Hub-and-spoke is N links and one address book.

| N | hub-and-spoke | mesh |
|---|---|---|
| 5 | 5 | 10 |
| 10 | 10 | 45 |
| 50 | 50 | 1225 |

Adding a device is one registration, not N new agreements.

## The price

- **Single point of failure.** No hub, no coordination at all (demo step 5). Real systems
  answer with hub redundancy, or by making spokes degrade gracefully when the hub is away.
- **Hub becomes the bottleneck**, for throughput and for change: every new behavior is a
  hub change.
- **Two extra hops** for anything that is really spoke-to-spoke.

## Variants worth naming

- **Authority direction.** In this toy the hub commands and spokes obey; spokes may only
  *report*. Some hubs are pure routers with no authority (a message broker); some are pure
  authority with no routing (a fleet controller pushing config). Decide which yours is.
- **Who initiates.** Hub-initiated (push) keeps control central; spoke-initiated (pull,
  e.g. spokes poll the hub for desired state) survives the hub being offline more gracefully
  and needs no inbound path to the spokes.
- **Hub as source of truth vs hub as coordinator.** The hub may hold the truth itself
  (`Hub.scenes` here) or merely point at where it lives (a git remote, a database) and
  coordinate reconciliation to it.

## Where you meet it

Airline route networks, VPN hub-and-spoke topologies, message brokers (spokes = producers
and consumers), MDM / fleet-management control planes, a star LAN around one switch, and
every "gateway" device in home automation (Home Assistant, Hue Bridge).

## Exercises

1. Add a second hub and make each spoke register with both. What broke, and what did the
   pattern lose?
2. Turn the hub into a pure router: delete `scenes`, keep `routes`. Which flows survive?
3. Invert initiation: spokes call `hub.desired_state(self.name)` on a timer instead of
   the hub calling `apply()`. What does the hub no longer need to know?
