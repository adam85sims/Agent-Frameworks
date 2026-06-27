"""Session State — Track active goals, status, and context across sessions.

Manages the .brain/ directory files (session.md, map.json, memory.md)
to provide structural awareness for autonomous agent workflows.

Usage:
    from automation.session import SessionState

    session = SessionState(root=Path("."))
    session.start("Implement feature X")
    session.update_status("in-progress")
    session.add_decision("Used library X because...")
    session.save()
"""

import json
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional

from common.logging import get_logger

logger = get_logger("automation.session")


class SessionState:
    """Manages session state files in .brain/ directory.

    Provides a Python interface for reading and writing session.md,
    map.json, and memory.md.
    """

    def __init__(self, root: Path = None):
        if root is None:
            root = Path.cwd()
        self.root = Path(root)
        self.brain_dir = self.root / ".brain"

        # State
        self.goal: str = ""
        self.status: str = "pending"
        self.next_steps: list[str] = []
        self.started_at: Optional[str] = None
        self.context_used: float = 0.0

        # Memory
        self.decisions: list[dict] = []
        self.gotchas: list[dict] = []

        # Map
        self.entry_points: list[str] = []
        self.key_components: dict = {}
        self.test_commands: list[str] = []

    def start(self, goal: str):
        """Start a new session with a goal."""
        self.goal = goal
        self.status = "in-progress"
        self.started_at = datetime.now(UTC).isoformat()
        self.next_steps = []
        logger.info("Session started: %s", goal)

    def update_status(self, status: str):
        """Update session status."""
        self.status = status
        logger.info("Status updated: %s", status)

    def add_next_step(self, step: str):
        """Add a next step."""
        self.next_steps.append(step)

    def add_decision(self, decision: str, reasoning: str = ""):
        """Log an architecture decision."""
        self.decisions.append({
            "date": datetime.now(UTC).isoformat(),
            "decision": decision,
            "reasoning": reasoning,
        })

    def add_gotcha(self, gotcha: str, fix: str = ""):
        """Log a gotcha/pitfall."""
        self.gotchas.append({
            "date": datetime.now(UTC).isoformat(),
            "gotcha": gotcha,
            "fix": fix,
        })

    def update_map(self, entry_points: list = None, key_components: dict = None,
                   test_commands: list = None):
        """Update the project map."""
        if entry_points is not None:
            self.entry_points = entry_points
        if key_components is not None:
            self.key_components = key_components
        if test_commands is not None:
            self.test_commands = test_commands

    def save(self):
        """Save all state files to .brain/."""
        self.brain_dir.mkdir(parents=True, exist_ok=True)
        self._save_session_md()
        self._save_memory_md()
        self._save_map_json()
        logger.info("Session state saved to %s", self.brain_dir)

    def load(self):
        """Load state from .brain/ files if they exist."""
        self._load_session_md()
        self._load_memory_md()
        self._load_map_json()

    def _save_session_md(self):
        """Write session.md."""
        content = f"""# Session State

- **Started:** {self.started_at or "unknown"}
- **Current Goal:** {self.goal or "Not set"}
- **Status:** {self.status}
- **Context Used:** {self.context_used:.0%}

## Active Tasks
"""
        for i, step in enumerate(self.next_steps, 1):
            content += f"{i}. {step}\n"

        if not self.next_steps:
            content += "(none)\n"

        (self.brain_dir / "session.md").write_text(content)

    def _save_memory_md(self):
        """Write memory.md."""
        content = "# Memory Log (Lessons Learned)\n\n"

        content += "## Architecture Decisions\n"
        content += "| Date | Decision | Reasoning |\n"
        content += "|------|----------|----------|\n"
        for d in self.decisions:
            content += f"| {d['date'][:10]} | {d['decision']} | {d['reasoning']} |\n"
        if not self.decisions:
            content += "| (none) | | |\n"

        content += "\n## Gotchas & Pitfalls\n"
        content += "| Date | Issue | Fix |\n"
        content += "|------|-------|-----|\n"
        for g in self.gotchas:
            content += f"| {g['date'][:10]} | {g['gotcha']} | {g['fix']} |\n"
        if not self.gotchas:
            content += "| (none) | | |\n"

        (self.brain_dir / "memory.md").write_text(content)

    def _save_map_json(self):
        """Write map.json."""
        data = {
            "entry_points": self.entry_points,
            "key_components": self.key_components,
            "test_commands": self.test_commands,
        }
        (self.brain_dir / "map.json").write_text(
            json.dumps(data, indent=2)
        )

    def _load_session_md(self):
        """Parse session.md if it exists."""
        path = self.brain_dir / "session.md"
        if not path.exists():
            return

        content = path.read_text()
        for line in content.split("\n"):
            # Strip markdown bold markers for cleaner parsing
            clean = line.replace("**", "")
            if clean.startswith("- Started:"):
                self.started_at = clean.split(":", 1)[1].strip()
            elif clean.startswith("- Current Goal:"):
                self.goal = clean.split(":", 1)[1].strip()
            elif clean.startswith("- Status:"):
                self.status = clean.split(":", 1)[1].strip()
            elif clean.startswith("- Context Used:"):
                try:
                    val = clean.split(":", 1)[1].strip().rstrip("%")
                    self.context_used = float(val) / 100
                except (ValueError, IndexError):
                    pass

    def _load_memory_md(self):
        """Parse memory.md if it exists."""
        path = self.brain_dir / "memory.md"
        if not path.exists():
            return

        # Simple parser — just check if sections have content
        content = path.read_text()
        if "## Gotchas" in content:
            lines = content.split("## Gotchas")[1].split("\n")
            for line in lines:
                if line.startswith("| ") and not line.startswith("| Date"):
                    parts = [p.strip() for p in line.split("|")[1:-1]]
                    if len(parts) >= 3 and parts[0] != "(none)":
                        self.gotchas.append({
                            "date": parts[0],
                            "gotcha": parts[1],
                            "fix": parts[2],
                        })

    def _load_map_json(self):
        """Parse map.json if it exists."""
        path = self.brain_dir / "map.json"
        if not path.exists():
            return

        try:
            data = json.loads(path.read_text())
            self.entry_points = data.get("entry_points", [])
            self.key_components = data.get("key_components", {})
            self.test_commands = data.get("test_commands", [])
        except json.JSONDecodeError:
            logger.warning("Failed to parse map.json")
