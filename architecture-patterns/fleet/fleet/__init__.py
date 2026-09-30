"""Fleet architecture, minimal: weather stations phoning home to one control plane.

    control_plane  cloud side: registry, /register + /heartbeat, desired state
    agent          station side: identity, backoff, register → heartbeat → reconcile
    workload       station side: the real job + its liveness signal
    demo           composition root + the scripted 6-phase scenario
"""
from .agent import Backoff, Outcome, StationAgent
from .control_plane import ControlPlane
from .workload import Workload

__all__ = ["Backoff", "ControlPlane", "Outcome", "StationAgent", "Workload"]
