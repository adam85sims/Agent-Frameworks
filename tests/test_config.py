"""Tests for common.config — layered configuration loading."""

import os
import tempfile
from pathlib import Path

import pytest

from common.config import Config, load_config


class TestConfigDefaults:
    """Config should return safe defaults when no files exist."""

    def test_load_config_with_no_file(self, tmp_path):
        result = load_config(root=tmp_path)
        assert isinstance(result, dict)
        assert "governance" in result
        assert "pattern_memory" in result
        assert "automation" in result

    def test_governance_defaults(self, tmp_path):
        result = load_config(root=tmp_path)
        gov = result["governance"]
        assert gov["src_dir"] == "src"
        assert gov["readme_path"] == "README.md"
        assert gov["diary_dir"] == "updates"
        assert gov["test_dir"] == "tests"
        assert gov["source_file_pattern"] == "**/*.py"
        assert gov["mcp_server_file"] is None

    def test_automation_defaults(self, tmp_path):
        result = load_config(root=tmp_path)
        auto = result["automation"]
        assert auto["exit_conditions"]["max_items_per_session"] == 3
        assert auto["exit_conditions"]["context_usage_limit"] == 0.6
        assert auto["work_queue"]["max_new_items_per_session"] == 2

    def test_pattern_memory_defaults(self, tmp_path):
        result = load_config(root=tmp_path)
        pm = result["pattern_memory"]
        assert "sqlite_path" in pm
        assert "chroma_path" in pm


class TestConfigYAMLOverride:
    """YAML file should override defaults."""

    def test_yaml_overrides_governance(self, tmp_path):
        config_file = tmp_path / "agent-frameworks.yaml"
        config_file.write_text("""
governance:
  src_dir: "lib"
  test_dir: "spec"
""")
        result = load_config(root=tmp_path)
        assert result["governance"]["src_dir"] == "lib"
        assert result["governance"]["test_dir"] == "spec"
        # Non-overridden defaults should remain
        assert result["governance"]["readme_path"] == "README.md"

    def test_yaml_creates_complete_section(self, tmp_path):
        config_file = tmp_path / "agent-frameworks.yaml"
        config_file.write_text("""
governance:
  src_dir: "app"
""")
        result = load_config(root=tmp_path)
        # Should have all governance keys, not just src_dir
        assert "readme_path" in result["governance"]
        assert "test_command" in result["governance"]


class TestConfigEnvOverride:
    """Environment variables should override YAML and defaults."""

    def test_env_overrides_default(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AGENT_FW_GOVERNANCE_SRC_DIR", "env_src")
        result = load_config(root=tmp_path)
        assert result["governance"]["src_dir"] == "env_src"

    def test_env_overrides_yaml(self, tmp_path, monkeypatch):
        config_file = tmp_path / "agent-frameworks.yaml"
        config_file.write_text("""
governance:
  src_dir: "yaml_src"
""")
        monkeypatch.setenv("AGENT_FW_GOVERNANCE_SRC_DIR", "env_src")
        result = load_config(root=tmp_path)
        assert result["governance"]["src_dir"] == "env_src"


class TestConfigClass:
    """Config object should provide dot-access and section access."""

    def test_get_section(self, tmp_path):
        config = Config(root=tmp_path)
        gov = config.get_section("governance")
        assert isinstance(gov, dict)
        assert "src_dir" in gov

    def test_get_value(self, tmp_path):
        config = Config(root=tmp_path)
        assert config.get("governance", "src_dir") == "src"

    def test_get_with_default(self, tmp_path):
        config = Config(root=tmp_path)
        assert config.get("governance", "nonexistent", "fallback") == "fallback"

    def test_set_value(self, tmp_path):
        config = Config(root=tmp_path)
        config.set("governance", "src_dir", "custom")
        assert config.get("governance", "src_dir") == "custom"


class TestConfigGracefulDegradation:
    """Config should work without PyYAML installed."""

    def test_missing_yaml_still_works(self, tmp_path):
        result = load_config(root=tmp_path)
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_malformed_yaml_uses_defaults(self, tmp_path):
        config_file = tmp_path / "agent-frameworks.yaml"
        config_file.write_text("{{{{invalid yaml:::")
        result = load_config(root=tmp_path)
        # Should fall back to defaults, not crash
        assert isinstance(result, dict)
        assert "governance" in result
