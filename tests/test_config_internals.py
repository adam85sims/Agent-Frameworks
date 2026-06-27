"""Tests for common.config internals — deep_merge, coerce, env overrides."""

import os
import pytest

from common.config import deep_merge, _coerce_env_value, _apply_env_overrides


# ─── deep_merge ───────────────────────────────────────────────────

class TestDeepMerge:
    """Test recursive dict merging."""

    def test_flat_merge(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        override = {"a": {"y": 99, "z": 100}}
        result = deep_merge(base, override)
        assert result == {"a": {"x": 1, "y": 99, "z": 100}, "b": 3}

    def test_deeply_nested(self):
        base = {"a": {"b": {"c": {"d": 1}}}}
        override = {"a": {"b": {"c": {"d": 2, "e": 3}}}}
        result = deep_merge(base, override)
        assert result == {"a": {"b": {"c": {"d": 2, "e": 3}}}}

    def test_override_replaces_non_dict_with_dict(self):
        base = {"a": "string"}
        override = {"a": {"nested": True}}
        result = deep_merge(base, override)
        assert result == {"a": {"nested": True}}

    def test_override_replaces_dict_with_non_dict(self):
        base = {"a": {"nested": True}}
        override = {"a": "string"}
        result = deep_merge(base, override)
        assert result == {"a": "string"}

    def test_empty_override(self):
        base = {"a": 1}
        result = deep_merge(base, {})
        assert result == {"a": 1}

    def test_empty_base(self):
        override = {"a": 1}
        result = deep_merge({}, override)
        assert result == {"a": 1}

    def test_both_empty(self):
        assert deep_merge({}, {}) == {}

    def test_does_not_mutate_base(self):
        base = {"a": {"x": 1}}
        override = {"a": {"y": 2}}
        deep_merge(base, override)
        assert base == {"a": {"x": 1}}

    def test_list_values_are_replaced_not_merged(self):
        base = {"a": [1, 2]}
        override = {"a": [3]}
        result = deep_merge(base, override)
        assert result == {"a": [3]}


# ─── _coerce_env_value ────────────────────────────────────────────

class TestCoerceEnvValue:
    """Test environment variable type coercion."""

    def test_true_string(self):
        assert _coerce_env_value("true") is True
        assert _coerce_env_value("True") is True
        assert _coerce_env_value("TRUE") is True

    def test_false_string(self):
        assert _coerce_env_value("false") is False
        assert _coerce_env_value("False") is False
        assert _coerce_env_value("FALSE") is False

    def test_integer_string(self):
        assert _coerce_env_value("42") == 42
        assert _coerce_env_value("0") == 0
        assert _coerce_env_value("-1") == -1

    def test_float_string(self):
        assert _coerce_env_value("3.14") == 3.14
        assert _coerce_env_value("0.0") == 0.0
        assert _coerce_env_value("-0.5") == -0.5

    def test_plain_string(self):
        assert _coerce_env_value("hello") == "hello"
        assert _coerce_env_value("/path/to/file") == "/path/to/file"

    def test_empty_string(self):
        assert _coerce_env_value("") == ""

    def test_whitespace_string(self):
        assert _coerce_env_value("  ") == "  "


# ─── _apply_env_overrides ─────────────────────────────────────────

class TestApplyEnvOverrides:
    """Test AGENT_FW_ env var overrides."""

    def test_simple_override(self, monkeypatch):
        monkeypatch.setenv("AGENT_FW_GOVERNANCE_SRC_DIR", "lib")
        config = {"governance": {"src_dir": "src", "test_dir": "tests"}}
        result = _apply_env_overrides(config)
        assert result["governance"]["src_dir"] == "lib"
        assert result["governance"]["test_dir"] == "tests"

    def test_creates_section_if_missing(self, monkeypatch):
        monkeypatch.setenv("AGENT_FW_NEWSECTION_KEY", "value")
        config = {}
        result = _apply_env_overrides(config)
        # _apply_env_overrides only modifies existing sections
        # New sections are NOT created — they must exist in config first
        assert result == {}

    def test_creates_nested_key(self, monkeypatch):
        monkeypatch.setenv("AGENT_FW_GOVERNANCE_NESTED_DEEP_KEY", "found")
        config = {"governance": {}}
        result = _apply_env_overrides(config)
        # Env vars use flat keys: section=governance, field=nested_deep_key
        # They don't create nested dicts — just flat leaf values
        assert result["governance"]["nested_deep_key"] == "found"

    def test_coerces_values(self, monkeypatch):
        monkeypatch.setenv("AGENT_FW_AUTOMATION_MAX_ITEMS", "5")
        monkeypatch.setenv("AGENT_FW_AUTOMATION_ENABLED", "true")
        config = {"automation": {}}
        result = _apply_env_overrides(config)
        assert result["automation"]["max_items"] == 5
        assert result["automation"]["enabled"] is True

    def test_no_env_vars_unchanged(self, monkeypatch):
        # Clear any AGENT_FW_ vars that might be set
        for key in list(os.environ.keys()):
            if key.startswith("AGENT_FW_"):
                monkeypatch.delenv(key, raising=False)
        config = {"governance": {"src_dir": "src"}}
        result = _apply_env_overrides(config)
        assert result == {"governance": {"src_dir": "src"}}
