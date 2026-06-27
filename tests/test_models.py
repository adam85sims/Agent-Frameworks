"""Tests for common.models — shared data structures."""

import pytest
from datetime import datetime

from common.models import (
    AuditResult,
    Claim,
    Discrepancy,
    Evidence,
    Severity,
    Verdict,
)


class TestSeverity:
    """Severity enum should have the three governance tiers."""

    def test_has_critical(self):
        assert Severity.CRITICAL == "CRITICAL"

    def test_has_warning(self):
        assert Severity.WARNING == "WARNING"

    def test_has_info(self):
        assert Severity.INFO == "INFO"


class TestVerdict:
    """Verdict enum should cover audit outcomes."""

    def test_has_pass(self):
        assert Verdict.PASS == "PASS"

    def test_has_warn(self):
        assert Verdict.WARN == "WARN"

    def test_has_fail(self):
        assert Verdict.FAIL == "FAIL"


class TestDiscrepancy:
    """Discrepancy should be a structured finding."""

    def test_create_minimal(self):
        d = Discrepancy(
            severity=Severity.CRITICAL,
            type="test_count_mismatch",
            description="Claimed 10, actual 8",
        )
        assert d.severity == Severity.CRITICAL
        assert d.claimed is None
        assert d.actual is None

    def test_create_full(self):
        d = Discrepancy(
            severity=Severity.WARNING,
            type="tool_count_mismatch",
            description="Tool count mismatch",
            claimed="13",
            actual="12",
        )
        assert d.claimed == "13"
        assert d.actual == "12"

    def test_to_dict(self):
        d = Discrepancy(
            severity=Severity.CRITICAL,
            type="test_count_mismatch",
            description="Failed tests",
            claimed="10",
            actual="8",
        )
        result = d.to_dict()
        assert result["severity"] == "CRITICAL"
        assert result["type"] == "test_count_mismatch"
        assert result["claimed"] == "10"

    def test_from_dict(self):
        data = {
            "severity": "WARNING",
            "type": "readme_mismatch",
            "description": "README outdated",
        }
        d = Discrepancy.from_dict(data)
        assert d.severity == Severity.WARNING
        assert d.type == "readme_mismatch"


class TestEvidence:
    """Evidence should hold all independently collected facts."""

    def test_create_minimal(self):
        e = Evidence(collected_at=datetime.now().isoformat())
        assert e.collected_at is not None
        assert e.tests_passed == 0
        assert e.tests_failed == 0

    def test_create_full(self):
        e = Evidence(
            collected_at="2026-06-27T12:00:00",
            tests_passed=10,
            tests_failed=0,
            tests_total=10,
            actual_tool_count=13,
            actual_test_count=10,
            source_files=["src/app.py", "src/utils.py"],
        )
        assert e.tests_passed == 10
        assert len(e.source_files) == 2

    def test_to_dict(self):
        e = Evidence(
            collected_at="2026-06-27T12:00:00",
            tests_passed=5,
            tests_failed=1,
        )
        result = e.to_dict()
        assert result["tests_passed"] == 5
        assert result["tests_failed"] == 1


class TestClaim:
    """Claim should represent extracted diary assertions."""

    def test_create_minimal(self):
        c = Claim(date="2026-06-27")
        assert c.date == "2026-06-27"
        assert c.test_counts == []
        assert c.tools_count == 0

    def test_create_full(self):
        c = Claim(
            date="2026-06-27",
            test_counts=[{"claimed_passing": 10, "claimed_total": 10}],
            tools_count=13,
            version="0.13.0",
            features=["conflict detection", "auto-confirm"],
            files_modified=["server.py", "storage.py"],
        )
        assert c.tools_count == 13
        assert len(c.features) == 2

    def test_to_dict(self):
        c = Claim(date="2026-06-27", tools_count=13)
        result = c.to_dict()
        assert result["date"] == "2026-06-27"
        assert result["tools_count"] == 13


class TestAuditResult:
    """AuditResult should be the top-level output of an audit."""

    def test_create_with_defaults(self):
        r = AuditResult(verdict=Verdict.PASS)
        assert r.verdict == Verdict.PASS
        assert r.discrepancies == []
        assert r.claims is None
        assert r.evidence is None

    def test_create_full(self):
        r = AuditResult(
            verdict=Verdict.FAIL,
            discrepancies=[
                Discrepancy(
                    severity=Severity.CRITICAL,
                    type="test_count_mismatch",
                    description="Tests claimed 10, actual 8",
                )
            ],
            summary="1 critical discrepancy",
            auditor_model="granite-4.1-3b",
        )
        assert r.verdict == Verdict.FAIL
        assert len(r.discrepancies) == 1
        assert r.auditor_model == "granite-4.1-3b"

    def test_critical_count(self):
        r = AuditResult(
            verdict=Verdict.FAIL,
            discrepancies=[
                Discrepancy(severity=Severity.CRITICAL, type="a", description="x"),
                Discrepancy(severity=Severity.WARNING, type="b", description="y"),
                Discrepancy(severity=Severity.CRITICAL, type="c", description="z"),
            ],
        )
        assert r.critical_count == 2
        assert r.warning_count == 1

    def test_to_dict(self):
        r = AuditResult(verdict=Verdict.PASS, summary="All clear")
        result = r.to_dict()
        assert result["verdict"] == "PASS"
        assert result["summary"] == "All clear"

    def test_from_dict(self):
        data = {
            "verdict": "WARN",
            "discrepancies": [
                {"severity": "WARNING", "type": "x", "description": "y"}
            ],
            "summary": "1 warning",
        }
        r = AuditResult.from_dict(data)
        assert r.verdict == Verdict.WARN
        assert len(r.discrepancies) == 1
