"""Tests for work queue round-trip fidelity."""

import pytest
from pathlib import Path

from automation.work_queue import WorkQueue


class TestWorkQueueRoundTrip:
    """WorkQueue.save() should produce TODO.md that round-trips exactly."""

    def _make_todo(self, tmp_path, content):
        (tmp_path / "TODO.md").write_text(content)

    def test_round_trip_preserves_pending(self, tmp_path):
        original = """# Work Queue

> Test queue.

## Rules
1. Pick the first item
2. Max 2 new items

## Pending
- [ ] Task alpha
- [ ] Task beta
- [ ] Task gamma

## Done
- [x] Old task

## Blocked
- [b] Needs input — waiting on user
"""
        self._make_todo(tmp_path, original)

        q1 = WorkQueue(root=tmp_path)
        q1.load()
        assert q1.pending_count() == 3
        assert q1.done_count() == 1
        assert q1.blocked_count() == 1

        q1.save()

        q2 = WorkQueue(root=tmp_path)
        q2.load()
        assert q2.pending_count() == 3
        assert q2.done_count() == 1
        assert q2.blocked_count() == 1

        # Verify item descriptions survived
        pending = [i for i in q2.items if i.status == "pending"]
        assert pending[0].description == "Task alpha"
        assert pending[1].description == "Task beta"
        assert pending[2].description == "Task gamma"

    def test_round_trip_after_complete(self, tmp_path):
        self._make_todo(tmp_path, """# Work Queue
## Pending
- [ ] First task
- [ ] Second task
## Done
## Blocked
""")
        q1 = WorkQueue(root=tmp_path)
        q1.load()
        item = q1.next_item()
        q1.complete(item.id)
        q1.save()

        q2 = WorkQueue(root=tmp_path)
        q2.load()
        assert q2.pending_count() == 1
        assert q2.done_count() == 1
        assert q2.items[0].description == "Second task"

    def test_round_trip_after_block(self, tmp_path):
        self._make_todo(tmp_path, """# Work Queue
## Pending
- [ ] Blockable task
## Done
## Blocked
""")
        q1 = WorkQueue(root=tmp_path)
        q1.load()
        item = q1.next_item()
        q1.block(item.id, "Needs API key from user")
        q1.save()

        q2 = WorkQueue(root=tmp_path)
        q2.load()
        assert q2.pending_count() == 0
        assert q2.blocked_count() == 1
        blocked = [i for i in q2.items if i.status == "blocked"][0]
        # Blocked items append the reason to the description on save
        # On reload, the full string becomes the description
        assert "Blockable task" in blocked.description
        assert "Needs API key from user" in blocked.description

    def test_round_trip_empty_queue(self, tmp_path):
        self._make_todo(tmp_path, """# Work Queue
## Pending
## Done
## Blocked
""")
        q1 = WorkQueue(root=tmp_path)
        q1.load()
        q1.save()

        q2 = WorkQueue(root=tmp_path)
        q2.load()
        assert q2.pending_count() == 0
        assert q2.done_count() == 0

    def test_round_trip_with_add_item(self, tmp_path):
        self._make_todo(tmp_path, """# Work Queue
## Pending
- [ ] Original task
## Done
## Blocked
""")
        q1 = WorkQueue(root=tmp_path)
        q1.load()
        q1.add_item("Newly discovered task")
        q1.save()

        q2 = WorkQueue(root=tmp_path)
        q2.load()
        assert q2.pending_count() == 2
        pending = [i for i in q2.items if i.status == "pending"]
        assert pending[0].description == "Original task"
        assert pending[1].description == "Newly discovered task"
