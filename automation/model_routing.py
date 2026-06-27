"""Model Routing — Config-driven task-to-model assignment.

Routes tasks to the optimal model based on capability classes defined
in agent-frameworks.yaml. No hardcoded model names.

Usage:
    from automation.model_routing import ModelRouter

    router = ModelRouter()
    model = router.route("research")         # -> {"provider": "...", "model": "..."}
    model = router.route("scaffolding")       # -> speed-tier model
    info = router.describe("code_review")     # -> routing metadata
"""

import sys
from pathlib import Path
from typing import Optional

from common.config import load_config
from common.logging import get_logger

logger = get_logger("automation.model_routing")

# ─── Capability categories ─────────────────────────────────────────
# These map task types to capability tiers.
# The config maps tiers to actual model names.

TASK_TO_TIER = {
    # Reasoning tier tasks
    "research": "reasoning",
    "problem_discovery": "reasoning",
    "architecture": "reasoning",
    "design": "reasoning",
    "code_review": "reasoning",
    "debugging": "reasoning",
    "complex_algorithms": "reasoning",
    "documentation": "reasoning",
    "synthesis": "reasoning",
    "planning": "reasoning",

    # Speed tier tasks
    "scaffolding": "speed",
    "crud": "speed",
    "test_stubs": "speed",
    "simple_ui": "speed",
    "boilerplate": "speed",
    "file_structure": "speed",
    "data_processing": "speed",
    "integration_glue": "speed",

    # Either tier (default to reasoning for safety)
    "core_implementation": "reasoning",
    "writing": "reasoning",
    "review": "reasoning",
}

# Default routing config if not specified in agent-frameworks.yaml
_DEFAULT_ROUTING = {
    "reasoning": {
        "models": [
            {"provider": "opencode-go", "model": "mimo-v2.5"},
        ],
        "use_for": [
            "research", "architecture", "code_review", "debugging",
            "complex_algorithms", "documentation", "synthesis", "planning",
        ],
    },
    "speed": {
        "models": [
            {"provider": "opencode-go", "model": "deepseek-v4-flash"},
        ],
        "use_for": [
            "scaffolding", "crud", "test_stubs", "simple_ui",
            "boilerplate", "file_structure", "data_processing",
            "integration_glue",
        ],
    },
}


class ModelRouter:
    """Config-driven model router that maps task types to models.

    Reads from agent-frameworks.yaml's automation.model_routing section.
    Falls back to sensible defaults if not configured.
    """

    def __init__(self, root: Path = None):
        if root is None:
            root = Path.cwd()
        self._config = load_config(root=Path(root))
        self._routing = self._config.get("automation", {}).get("model_routing", {})

        # Merge with defaults for any missing tiers
        for tier, default in _DEFAULT_ROUTING.items():
            if tier not in self._routing:
                self._routing[tier] = default

    def route(self, task_type: str) -> dict:
        """Get the best model for a task type.

        Args:
            task_type: Task identifier (e.g., "research", "scaffolding").

        Returns:
            Dict with 'provider' and 'model' keys.
        """
        tier = TASK_TO_TIER.get(task_type, "reasoning")
        tier_config = self._routing.get(tier, _DEFAULT_ROUTING.get(tier, {}))
        models = tier_config.get("models", [])

        if not models:
            # Ultimate fallback
            return {"provider": "opencode-go", "model": "mimo-v2.5"}

        return models[0]

    def route_all(self, task_type: str) -> list[dict]:
        """Get all models for a task type (for delegation chains).

        Args:
            task_type: Task identifier.

        Returns:
            List of model dicts, ordered by preference.
        """
        tier = TASK_TO_TIER.get(task_type, "reasoning")
        tier_config = self._routing.get(tier, _DEFAULT_ROUTING.get(tier, {}))
        return tier_config.get("models", [])

    def describe(self, task_type: str) -> dict:
        """Get routing metadata for a task type.

        Returns:
            Dict with task_type, tier, models, and use_for list.
        """
        tier = TASK_TO_TIER.get(task_type, "reasoning")
        tier_config = self._routing.get(tier, _DEFAULT_ROUTING.get(tier, {}))
        return {
            "task_type": task_type,
            "tier": tier,
            "models": tier_config.get("models", []),
            "use_for": tier_config.get("use_for", []),
        }

    def list_tasks(self) -> dict:
        """List all known task types and their tiers.

        Returns:
            Dict of task_type -> tier.
        """
        return dict(TASK_TO_TIER)

    def list_tiers(self) -> dict:
        """List all configured tiers and their models.

        Returns:
            Dict of tier -> {"models": [...], "use_for": [...]}.
        """
        return dict(self._routing)


def route_task(task_type: str, root: Path = None) -> dict:
    """Convenience function: route a task to the best model.

    Args:
        task_type: Task identifier.
        root: Project root for config lookup.

    Returns:
        Dict with 'provider' and 'model' keys.
    """
    router = ModelRouter(root=root)
    return router.route(task_type)
