# Fleet (toy example)

*Weather stations phoning home to one control plane, in ~330 lines of stdlib Python (docstrings included): a four-module package plus a notebook.*

```sh
# from this folder
uv run python -m fleet.demo                             # scripted, 6 phases
uv run --with jupyterlab jupyter lab fleet.ipynb        # interactive walkthrough
```

```
fleet/                  ← this example
├── fleet/              ← the package (stdlib only, no install: run from this folder)
│   ├── __init__.py     re-exports ControlPlane, StationAgent, Workload, Backoff, Outcome
│   ├── control_plane.py
│   ├── agent.py
│   ├── workload.py
│   └── demo.py
├── fleet.ipynb
└── README.md
```

| Module | Side | What it holds |
|---|---|---|
| `fleet/control_plane.py` | cloud | registry, `/register` + `/heartbeat`, desired state, dashboard |
| `fleet/agent.py` | station | identity, `Outcome`, backoff, the register → heartbeat → reconcile loop |
| `fleet/workload.py` | station | the real job (take readings) + its liveness signal |
| `fleet/demo.py` | — | composition root (`start_station`) and the scripted scenario; the notebook reuses `start_station` |

## The idea

Many **agents**, one **control plane**. Each agent calls *out*: it registers once, then
heartbeats forever. The control plane never calls an agent. It answers, remembers, and
infers everything from what arrives and from what *stops* arriving.

```
   rooftop-A              hilltop-B              valley-C
  ┌──────────────┐       ┌──────────────┐       ┌──────────────┐
  │ workload     │       │ workload     │       │ workload     │
  │   │ alive?   │       │   │ alive?   │       │   │ alive?   │
  │   ▼          │       │   ▼          │       │   ▼          │
  │ agent        │       │ agent        │       │ agent        │
  └──┬───────────┘       └──┬───────────┘       └──┬───────────┘
     │ POST /register, /heartbeat  (outbound only) │
     └───────────────────┬─────────────────────────┘
                         ▼
               ┌────────────────────┐   reply: 200 {latest_firmware}
               │   CONTROL PLANE    │          401 → register again
               │ registry{id→record}│          503 → back off
               │ last_seen · stats  │
               │ latest_firmware    │ ◄── operator sets desired state
               └────────────────────┘
```

## Seven ideas, and where each lives

| # | Idea | In the code |
|---|---|---|
| 1 | **Outbound only.** The agent holds a handle to the plane; the plane holds none back. A station behind NAT or a firewall needs no open port. | `StationAgent.plane`; `ControlPlane` has no agent references |
| 2 | **Stable identity.** An id persisted on the device, so a reboot is the same station, not a new one. | `load_or_create_id()` |
| 3 | **Idempotent registration.** An upsert keyed by id, so registering twice is harmless. | `ControlPlane._register()` |
| 4 | **Health inferred from silence.** The plane never probes. `online`/`STALE` comes from how old `last_seen` is. | `ControlPlane.dashboard()` |
| 5 | **Desired state on the reply.** Every 200 carries `latest_firmware`; the agent reconciles toward it and reports the result on the next heartbeat. | `_desired_state()`, `StationAgent._reconcile()` |
| 6 | **Self-healing.** If the plane forgets a station, the heartbeat gets 401 and the agent registers again. The registry rebuilds itself. | `Outcome.UNREGISTERED` branch |
| 7 | **Backoff with full jitter.** Failures grow the retry window; the random delay keeps a recovering plane from being stampeded. | `Backoff` |
| + | **Link health ≠ work health.** The process can heartbeat while its real job is hung, so the agent reports the workload's liveness separately. | `Workload.is_alive` → `stats["workload_alive"]` |

The agent loop is one `match` on three outcomes. That table *is* the agent's policy:

| Reply | `Outcome` | Agent does |
|---|---|---|
| 200 | `OK` | reset backoff, reconcile to desired state, sleep `interval` |
| 401 | `UNREGISTERED` | register again (the plane forgot us) |
| 5xx, anything else | `FAILURE` | sleep a jittered backoff, retry |

## Six phases the demo shows

1. **Startup.** Every station registers, then heartbeats. Some `503 → backoff` lines are the simulated flaky network.
2. **Silent death.** valley-C loses power. Nothing tells the plane; its row turns `STALE`
   once heartbeats stop. The other columns in a stale row are *last known* values.
3. **Reboot.** valley-C comes back with the same id file, so it's the same row, no duplicate.
4. **Hung sensor.** hilltop-B's link stays `online` but its workload shows `DEAD` (and its temperature stops changing).
5. **Plane restart.** The registry is wiped. Every station gets a 401, registers again, and the dashboard refills. The plane needed no backup of "who exists".
6. **Rollout.** The operator sets `latest_firmware = "2.1.0"`. That's one value on the plane, and no push. Rows show `*` until each station's next heartbeat reports the new version.

## Why it works

- **Scale follows the agents.** Adding a station is starting an agent. The plane learns it exists from the first `/register`.
- **The station is the source of truth for itself** (existence, firmware, health). The plane
  holds a cache of those facts plus the one thing it owns: desired state. Losing the cache
  is cheap, as phase 5 shows.
- **One direction of trust and networking.** Only the plane needs to be reachable, which
  is what makes this viable for devices on a hospital LAN, a home router, or a cell modem.

## The price

- **Latency of control.** The plane can only speak when an agent calls. A command waits up to one
  heartbeat interval, and an offline station never receives it.
- **Detection lag vs load.** `STALE` needs `stale_after` > interval. A shorter interval
  gives faster detection and more requests (N stations ÷ interval per second).
- **"Stale" is ambiguous.** A dead station, a dead link, and a partitioned plane look identical from the plane's side.
- **The plane is still a hub.** If it's down, the fleet keeps working but becomes invisible and unmanageable. See [hub-and-spoke](../hub-and-spoke/).

## What the toy leaves out

Authentication (API keys, mTLS), real HTTP and timeouts, persistence of the registry, a
real update mechanism (download, verify, swap, report), and a `STALE` alert. None change the
shape: they fill in the boxes.

## Where you meet it

MDM (Intune, Jamf), IoT device management (AWS IoT, Azure IoT Hub device twins), Kubernetes
(the kubelet heartbeats to the API server; node `Ready` is inferred from lease age),
CI runners (GitHub Actions self-hosted runners poll for jobs), Tailscale/ZeroTier clients,
and on-prem AI appliances that phone home to a vendor cloud.

## Exercises

1. Delete `valley-C.id` before phase 3. What does the dashboard show, and why does the old row never go away? Add a rule to the plane that fixes it.
2. Make `Backoff.next()` return `window` with no jitter, raise the station count to 50, and
   make the plane fail 100% for a second. Count requests per 50 ms after it recovers.
3. Add a second piece of desired state (`sample_period`) and have `_reconcile()` apply it
   to the workload. What changes on the plane? (Nothing but one dict key.)
4. Give the plane a command queue: `plane.commands[station_id] = ["reboot"]`, delivered in
   the next heartbeat reply. You've just built "push" on top of pull.
