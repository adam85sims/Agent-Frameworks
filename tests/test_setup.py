"""Tests for the setup CLI — detection, init, check, doctor."""

import json
from pathlib import Path

import pytest

from common.setup_cli import EnvDetector, action_init, action_check, action_doctor


class TestEnvDetector:
    """Environment detection should identify Python, agents, backends."""

    def test_detect_python(self, tmp_path):
        detector = EnvDetector(root=tmp_path)
        py = detector.detect_python()
        assert "version" in py
        assert py["ok"] is True  # Python 3.14 > 3.11

    def test_detect_agents_returns_dict(self, tmp_path):
        detector = EnvDetector(root=tmp_path)
        agents = detector.detect_agents()
        assert isinstance(agents, dict)
        # Should have at least these keys
        for key in ["claude-desktop", "hermes", "opencode", "cursor"]:
            assert key in agents
            assert "status" in agents[key]

    def test_detect_llm_backends_returns_dict(self, tmp_path):
        detector = EnvDetector(root=tmp_path)
        backends = detector.detect_llm_backends()
        assert isinstance(backends, dict)

    def test_detect_containers_returns_dict(self, tmp_path):
        detector = EnvDetector(root=tmp_path)
        containers = detector.detect_containers()
        assert isinstance(containers, dict)

    def test_detect_existing_config(self, tmp_path):
        detector = EnvDetector(root=tmp_path)
        config = detector.detect_existing_config()
        assert config["config_file"]["exists"] is False
        assert config["governance_dir"]["exists"] is False

    def test_detect_existing_config_with_files(self, tmp_path):
        (tmp_path / "agent-frameworks.yaml").write_text("test: true")
        (tmp_path / "governance").mkdir()
        detector = EnvDetector(root=tmp_path)
        config = detector.detect_existing_config()
        assert config["config_file"]["exists"] is True
        assert config["governance_dir"]["exists"] is True

    def test_detect_all(self, tmp_path):
        detector = EnvDetector(root=tmp_path)
        results = detector.detect_all()
        assert "python" in results
        assert "agents" in results
        assert "llm_backends" in results
        assert "containers" in results
        assert "existing_config" in results


class TestActionInit:
    """Init should create project structure."""

    def test_creates_config_file(self, tmp_path):
        class Args:
            root = str(tmp_path)
            force = False
            yes = True
        action_init(Args())
        assert (tmp_path / "agent-frameworks.yaml").exists()

    def test_creates_governance_dir(self, tmp_path):
        class Args:
            root = str(tmp_path)
            force = False
            yes = True
        action_init(Args())
        assert (tmp_path / "governance").exists()
        assert (tmp_path / "governance" / "governance.yaml").exists()
        assert (tmp_path / "governance" / "auditor.yaml").exists()

    def test_creates_brain_dir(self, tmp_path):
        class Args:
            root = str(tmp_path)
            force = False
            yes = True
        action_init(Args())
        assert (tmp_path / ".brain").exists()
        assert (tmp_path / ".brain" / "session.md").exists()
        assert (tmp_path / ".brain" / "memory.md").exists()
        assert (tmp_path / ".brain" / "map.json").exists()

    def test_creates_todo(self, tmp_path):
        class Args:
            root = str(tmp_path)
            force = False
            yes = True
        action_init(Args())
        assert (tmp_path / "TODO.md").exists()
        content = (tmp_path / "TODO.md").read_text()
        assert "Pending" in content

    def test_creates_updates_dir(self, tmp_path):
        class Args:
            root = str(tmp_path)
            force = False
            yes = True
        action_init(Args())
        assert (tmp_path / "updates").exists()

    def test_idempotent(self, tmp_path):
        class Args:
            root = str(tmp_path)
            force = False
            yes = True
        action_init(Args())
        action_init(Args())  # Second run should not fail


class TestActionCheck:
    """Check should verify project structure."""

    def test_check_on_empty_project(self, tmp_path, capsys):
        class Args:
            root = str(tmp_path)
        action_check(Args())
        captured = capsys.readouterr()
        assert "agent-frameworks.yaml missing" in captured.out

    def test_check_on_initiated_project(self, tmp_path, capsys):
        class Args:
            root = str(tmp_path)
            force = False
            yes = True
        action_init(Args())
        action_check(Args())
        captured = capsys.readouterr()
        assert "All checks passed" in captured.out


class TestActionDoctor:
    """Doctor should fix common problems."""

    def test_doctor_creates_missing_dirs(self, tmp_path, capsys):
        class Args:
            root = str(tmp_path)
        action_doctor(Args())
        assert (tmp_path / "governance").exists()
        assert (tmp_path / ".brain").exists()
        assert (tmp_path / "updates").exists()

    def test_doctor_creates_config(self, tmp_path, capsys):
        class Args:
            root = str(tmp_path)
        action_doctor(Args())
        assert (tmp_path / "agent-frameworks.yaml").exists()

    def test_doctor_on_healthy_project(self, tmp_path, capsys):
        class Args:
            root = str(tmp_path)
            force = False
            yes = True
        action_init(Args())
        action_doctor(Args())
        captured = capsys.readouterr()
        assert "No issues found" in captured.out
