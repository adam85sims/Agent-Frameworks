"""Work Queue — Persistent TODO.md task management.

Manages the TODO.md file as the single source of truth for autonomous
agent sessions. Tracks pending, done, and blocked items with exit conditions.

Usage:
    from automation.work_queue import WorkQueue

    queue = WorkQueue(root=Path("."))
    queue.load()
    item = queue.next_item()  # Get first pending item
    queue.complete(item.id, "Implemented feature X")
    queue.save()
"""

import re
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional

from common.config import load_config
from common.logging import get_logger

logger = get_logger("automation.work_queue")


class WorkItem:
    """A single work item from TODO.md."""

    def __init__(self, id: str, description: str, status: str = "pending",
                 section: str = "Pending"):
        self.id = id
        self.description = description
        self.status = status  # pending, done, blocked
        self.section = section
        self.completed_at: Optional[str] = None
        self.blocked_reason: Optional[str] = None

    def __repr__(self):
        return f"WorkItem({self.id}, {self.status}, {self.description[:40]})"


class WorkQueue:
    """Manages TODO.md as a persistent work queue.

    Reads and writes TODO.md in a structured format with
    Pending, Done, and Blocked sections.
    """

    def __init__(self, root: Path = None):
        if root is None:
            root = Path.cwd()
        self.root = Path(root)
        self.todo_path = self.root / "TODO.md"
        self.items: list[WorkItem] = []
        self.completed_this_session: int = 0

        # Load exit conditions from config
        config = load_config(root=self.root)
        auto_cfg = config.get("automation", {})
        exit_cfg = auto_cfg.get("exit_conditions", {})
        self.max_items_per_session = exit_cfg.get("max_items_per_session", 3)
        self.context_usage_limit = exit_cfg.get("context_usage_limit", 0.6)
        self.max_consecutive_failures = exit_cfg.get("max_consecutive_failures", 3)
        self.require_governance_pass = exit_cfg.get("require_governance_pass", True)

        queue_cfg = auto_cfg.get("work_queue", {})
        self.max_new_items_per_session = queue_cfg.get("max_new_items_per_session", 2)

    def load(self):
        """Load items from TODO.md."""
        self.items = []
        if not self.todo_path.exists():
            logger.info("No TODO.md found at %s", self.todo_path)
            return

        content = self.todo_path.read_text()
        current_section = "Pending"

        for line in content.split("\n"):
            line = line.strip()

            # Detect section headers
            if line.startswith("## "):
                current_section = line[3:].strip()
                continue

            # Detect items: - [ ] or - [x] or - [b]
            match = re.match(r"^-\s+\[([ xXb])\]\s+(.+)$", line)
            if match:
                marker = match.group(1)
                description = match.group(2)

                if marker in ("x", "X"):
                    status = "done"
                elif marker == "b":
                    status = "blocked"
                else:
                    status = "pending"

                item = WorkItem(
                    id=f"item-{len(self.items)}",
                    description=description,
                    status=status,
                    section=current_section,
                )
                self.items.append(item)

        logger.info("Loaded %d items from TODO.md", len(self.items))

    def save(self):
        """Save items back to TODO.md."""
        content = "# Work Queue\n\n"
        content += "> The agent works through this list top-to-bottom during each session.\n"
        content += "> Pick the first unchecked item. Mark done when complete.\n\n"

        # Pending section
        content += "## Pending\n\n"
        pending = [i for i in self.items if i.status == "pending"]
        if pending:
            for item in pending:
                content += f"- [ ] {item.description}\n"
        else:
            content += "(empty)\n"

        # Done section
        content += "\n## Done\n\n"
        done = [i for i in self.items if i.status == "done"]
        if done:
            for item in done:
                content += f"- [x] {item.description}"
                if item.completed_at:
                    content += f" (completed: {item.completed_at[:10]})"
                content += "\n"
        else:
            content += "(empty)\n"

        # Blocked section
        content += "\n## Blocked\n\n"
        blocked = [i for i in self.items if i.status == "blocked"]
        if blocked:
            for item in blocked:
                content += f"- [b] {item.description}"
                if item.blocked_reason:
                    content += f" — {item.blocked_reason}"
                content += "\n"
        else:
            content += "(empty)\n"

        self.todo_path.write_text(content)
        logger.info("Saved %d items to TODO.md", len(self.items))

    def next_item(self) -> Optional[WorkItem]:
        """Get the next pending item (first unchecked)."""
        for item in self.items:
            if item.status == "pending":
                return item
        return None

    def complete(self, item_id: str, notes: str = ""):
        """Mark an item as done."""
        for item in self.items:
            if item.id == item_id:
                item.status = "done"
                item.completed_at = datetime.now(UTC).isoformat()
                self.completed_this_session += 1
                logger.info("Completed: %s", item.description[:50])
                return
        logger.warning("Item not found: %s", item_id)

    def block(self, item_id: str, reason: str):
        """Mark an item as blocked."""
        for item in self.items:
            if item.id == item_id:
                item.status = "blocked"
                item.blocked_reason = reason
                logger.info("Blocked: %s — %s", item.description[:50], reason)
                return

    def add_item(self, description: str, section: str = "Pending") -> WorkItem:
        """Add a new item to the queue."""
        item = WorkItem(
            id=f"item-{len(self.items)}",
            description=description,
            status="pending",
            section=section,
        )
        self.items.append(item)
        logger.info("Added: %s", description[:50])
        return item

    def should_exit(self, context_usage: float = 0.0) -> Optional[str]:
        """Check if the session should exit.

        Returns:
            Exit reason string if should exit, None if OK to continue.
        """
        # Check 1: Queue empty
        pending = [i for i in self.items if i.status == "pending"]
        if not pending:
            return "queue_empty"

        # Check 2: Too many items completed
        if self.completed_this_session >= self.max_items_per_session:
            return "max_items_completed"

        # Check 3: Context usage too high
        if context_usage >= self.context_usage_limit:
            return "context_usage_high"

        # Check 4: Has blocked items that need user input
        blocked = [i for i in self.items if i.status == "blocked"]
        if blocked:
            return "has_blocked_items"

        return None

    def pending_count(self) -> int:
        """Count pending items."""
        return sum(1 for i in self.items if i.status == "pending")

    def done_count(self) -> int:
        """Count done items."""
        return sum(1 for i in self.items if i.status == "done")

    def blocked_count(self) -> int:
        """Count blocked items."""
        return sum(1 for i in self.items if i.status == "blocked")
