"""Agent Frameworks — Automation Module

Config-driven model routing, session state, and work queue management
for autonomous AI agent workflows.

Usage:
    from automation import ModelRouter, SessionState, WorkQueue

    router = ModelRouter()
    model = router.route("research")  # returns best model for research
    model = router.route("scaffolding")  # returns best model for scaffolding
"""

from automation.model_routing import ModelRouter, route_task
from automation.session import SessionState
from automation.work_queue import WorkQueue

__all__ = [
    "ModelRouter",
    "route_task",
    "SessionState",
    "WorkQueue",
]
