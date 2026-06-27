"""Tests for automation module — model routing, session state, work queue."""

import json
from pathlib import Path

import pytest


# ─── Model Routing ─────────────────────────────────────────────────

class TestModelRouter:
    """Model routing should be config-driven by capability tier."""

    def test_route_reasoning_task(self, tmp_path):
        from automation.model_routing import ModelRouter
        router = ModelRouter(root=tmp_path)
        model = router.route("research")
        assert "provider" in model
        assert "model" in model

    def test_route_speed_task(self, tmp_path):
        from automation.model_routing import ModelRouter
        router = ModelRouter(root=tmp_path)
        model = router.route("scaffolding")
        assert "provider" in model
        assert "model" in model

    def test_unknown_task_defaults_to_reasoning(self, tmp_path):
        from automation.model_routing import ModelRouter
        router = ModelRouter(root=tmp_path)
        model = router.route("some_unknown_task")
        assert "provider" in model

    def test_describe_returns_metadata(self, tmp_path):
        from automation.model_routing import ModelRouter
        router = ModelRouter(root=tmp_path)
        info = router.describe("research")
        assert info["task_type"] == "research"
        assert info["tier"] == "reasoning"
        assert "models" in info

    def test_list_tasks(self, tmp_path):
        from automation.model_routing import ModelRouter
        router = ModelRouter(root=tmp_path)
        tasks = router.list_tasks()
        assert "research" in tasks
        assert "scaffolding" in tasks
        assert tasks["research"] == "reasoning"
        assert tasks["scaffolding"] == "speed"

    def test_list_tiers(self, tmp_path):
        from automation.model_routing import ModelRouter
        router = ModelRouter(root=tmp_path)
        tiers = router.list_tiers()
        assert "reasoning" in tiers
        assert "speed" in tiers

    def test_route_all_returns_list(self, tmp_path):
        from automation.model_routing import ModelRouter
        router = ModelRouter(root=tmp_path)
        models = router.route_all("research")
        assert isinstance(models, list)
        assert len(models) >= 1

    def test_convenience_function(self, tmp_path):
        from automation.model_routing import route_task
        model = route_task("debugging", root=tmp_path)
        assert "provider" in model
        assert "model" in model

    def test_config_overrides_default(self, tmp_path):
        config_file = tmp_path / "agent-frameworks.yaml"
        config_file.write_text("""
automation:
  model_routing:
    reasoning:
      models:
        - provider: "custom"
          model: "custom-reasoning-model"
      use_for: ["research"]
""")
        from automation.model_routing import ModelRouter
        router = ModelRouter(root=tmp_path)
        model = router.route("research")
        assert model["provider"] == "custom"
        assert model["model"] == "custom-reasoning-model"


# ─── Session State ─────────────────────────────────────────────────

class TestSessionState:
    """Session state should track goals, decisions, and map."""

    def test_start_session(self, tmp_path):
        from automation.session import SessionState
        session = SessionState(root=tmp_path)
        session.start("Build feature X")
        assert session.goal == "Build feature X"
        assert session.status == "in-progress"
        assert session.started_at is not None

    def test_update_status(self, tmp_path):
        from automation.session import SessionState
        session = SessionState(root=tmp_path)
        session.start("Test")
        session.update_status("blocked")
        assert session.status == "blocked"

    def test_add_decision(self, tmp_path):
        from automation.session import SessionState
        session = SessionState(root=tmp_path)
        session.add_decision("Used pytest", "Better fixture support")
        assert len(session.decisions) == 1
        assert session.decisions[0]["decision"] == "Used pytest"

    def test_add_gotcha(self, tmp_path):
        from automation.session import SessionState
        session = SessionState(root=tmp_path)
        session.add_gotcha("ChromaDB leaks handles", "Call _ensure_collection")
        assert len(session.gotchas) == 1

    def test_save_and_load(self, tmp_path):
        from automation.session import SessionState
        session = SessionState(root=tmp_path)
        session.start("Test feature")
        session.add_decision("Decision A", "Reason A")
        session.add_gotcha("Gotcha B", "Fix B")
        session.update_map(entry_points=["src/main.py"], test_commands=["pytest"])
        session.save()

        # Load into new session
        session2 = SessionState(root=tmp_path)
        session2.load()
        assert session2.goal == "Test feature"
        assert session2.started_at is not None

    def test_save_creates_brain_dir(self, tmp_path):
        from automation.session import SessionState
        session = SessionState(root=tmp_path)
        session.start("Test")
        session.save()
        assert (tmp_path / ".brain").exists()
        assert (tmp_path / ".brain" / "session.md").exists()
        assert (tmp_path / ".brain" / "memory.md").exists()
        assert (tmp_path / ".brain" / "map.json").exists()

    def test_session_md_content(self, tmp_path):
        from automation.session import SessionState
        session = SessionState(root=tmp_path)
        session.start("Build API")
        session.add_next_step("Create models")
        session.add_next_step("Write endpoints")
        session.save()

        content = (tmp_path / ".brain" / "session.md").read_text()
        assert "Build API" in content
        assert "Create models" in content
        assert "Write endpoints" in content

    def test_map_json_content(self, tmp_path):
        from automation.session import SessionState
        session = SessionState(root=tmp_path)
        session.update_map(
            entry_points=["app.py"],
            key_components={"core": "src/core/"},
            test_commands=["pytest tests/"],
        )
        session.save()

        data = json.loads((tmp_path / ".brain" / "map.json").read_text())
        assert data["entry_points"] == ["app.py"]
        assert data["key_components"]["core"] == "src/core/"


# ─── Work Queue ────────────────────────────────────────────────────

class TestWorkQueue:
    """Work queue should manage TODO.md items with exit conditions."""

    def _make_todo(self, tmp_path, content):
        (tmp_path / "TODO.md").write_text(content)

    def test_load_empty_queue(self, tmp_path):
        from automation.work_queue import WorkQueue
        queue = WorkQueue(root=tmp_path)
        queue.load()
        assert queue.pending_count() == 0

    def test_load_pending_items(self, tmp_path):
        from automation.work_queue import WorkQueue
        self._make_todo(tmp_path, """# Work Queue
## Pending
- [ ] Task one
- [ ] Task two
## Done
- [x] Old task
## Blocked
""")
        queue = WorkQueue(root=tmp_path)
        queue.load()
        assert queue.pending_count() == 2
        assert queue.done_count() == 1

    def test_next_item_returns_first_pending(self, tmp_path):
        from automation.work_queue import WorkQueue
        self._make_todo(tmp_path, """# Work Queue
## Pending
- [ ] First task
- [ ] Second task
## Done
## Blocked
""")
        queue = WorkQueue(root=tmp_path)
        queue.load()
        item = queue.next_item()
        assert item is not None
        assert "First task" in item.description

    def test_next_item_returns_none_when_empty(self, tmp_path):
        from automation.work_queue import WorkQueue
        self._make_todo(tmp_path, """# Work Queue
## Pending
## Done
## Blocked
""")
        queue = WorkQueue(root=tmp_path)
        queue.load()
        assert queue.next_item() is None

    def test_complete_item(self, tmp_path):
        from automation.work_queue import WorkQueue
        self._make_todo(tmp_path, """# Work Queue
## Pending
- [ ] Task one
## Done
## Blocked
""")
        queue = WorkQueue(root=tmp_path)
        queue.load()
        item = queue.next_item()
        queue.complete(item.id)
        assert item.status == "done"
        assert queue.done_count() == 1
        assert queue.completed_this_session == 1

    def test_block_item(self, tmp_path):
        from automation.work_queue import WorkQueue
        self._make_todo(tmp_path, """# Work Queue
## Pending
- [ ] Task one
## Done
## Blocked
""")
        queue = WorkQueue(root=tmp_path)
        queue.load()
        item = queue.next_item()
        queue.block(item.id, "Needs user input")
        assert item.status == "blocked"
        assert item.blocked_reason == "Needs user input"

    def test_save_and_reload(self, tmp_path):
        from automation.work_queue import WorkQueue
        self._make_todo(tmp_path, """# Work Queue
## Pending
- [ ] Task one
- [ ] Task two
## Done
## Blocked
""")
        queue = WorkQueue(root=tmp_path)
        queue.load()
        item = queue.next_item()
        queue.complete(item.id)
        queue.save()

        # Reload and verify
        queue2 = WorkQueue(root=tmp_path)
        queue2.load()
        assert queue2.pending_count() == 1
        assert queue2.done_count() == 1

    def test_should_exit_queue_empty(self, tmp_path):
        from automation.work_queue import WorkQueue
        self._make_todo(tmp_path, """# Work Queue
## Pending
## Done
## Blocked
""")
        queue = WorkQueue(root=tmp_path)
        queue.load()
        assert queue.should_exit() == "queue_empty"

    def test_should_exit_max_items(self, tmp_path):
        from automation.work_queue import WorkQueue
        self._make_todo(tmp_path, """# Work Queue
## Pending
- [ ] Task
## Done
## Blocked
""")
        queue = WorkQueue(root=tmp_path)
        queue.load()
        queue.completed_this_session = 3  # At limit
        assert queue.should_exit() == "max_items_completed"

    def test_should_exit_context_high(self, tmp_path):
        from automation.work_queue import WorkQueue
        self._make_todo(tmp_path, """# Work Queue
## Pending
- [ ] Task
## Done
## Blocked
""")
        queue = WorkQueue(root=tmp_path)
        queue.load()
        assert queue.should_exit(context_usage=0.7) == "context_usage_high"

    def test_should_continue_when_ok(self, tmp_path):
        from automation.work_queue import WorkQueue
        self._make_todo(tmp_path, """# Work Queue
## Pending
- [ ] Task
## Done
## Blocked
""")
        queue = WorkQueue(root=tmp_path)
        queue.load()
        assert queue.should_exit() is None

    def test_add_item(self, tmp_path):
        from automation.work_queue import WorkQueue
        self._make_todo(tmp_path, """# Work Queue
## Pending
## Done
## Blocked
""")
        queue = WorkQueue(root=tmp_path)
        queue.load()
        queue.add_item("New task from session")
        assert queue.pending_count() == 1

    def test_blocked_items_trigger_exit(self, tmp_path):
        from automation.work_queue import WorkQueue
        self._make_todo(tmp_path, """# Work Queue
## Pending
- [ ] Task
## Done
## Blocked
- [b] Blocked task — needs input
""")
        queue = WorkQueue(root=tmp_path)
        queue.load()
        assert queue.should_exit() == "has_blocked_items"
