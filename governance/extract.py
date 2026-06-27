#!/usr/bin/env python3
"""Post-process auditor output to extract structured findings.

Replaces the Gemma-era version that relied on regex extraction from
reasoning-loop transcripts. The new model emits a strict JSON object;
we parse it directly. The deterministic claim-vs-evidence compare
in this file is still the ultimate safety net.

Key changes (2026-06-24):
  - Parses strict JSON output (no more regex on chain-of-thought)
  - Adds future-date rule (catches backdated "today is 2026-06-30")
  - Treats empty raw_report as CRITICAL (was silent before)
  - Treats "AUDITOR ERROR:" prefix as CRITICAL
  - Model findings + comparator findings are merged; CRITICAL wins
"""

import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional


def _safe_load_json(text: str) -> Optional[dict]:
    """Try to parse a JSON object out of a model response.

    Models occasionally wrap JSON in markdown fences or add a stray
    preamble. We try a few patterns before giving up.
    """
    if not text:
        return None

    text = text.strip()

    # 1. Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Strip markdown fence
    fence_match = re.search(
        r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL
    )
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # 3. Find first { ... last } span
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and last > first:
        try:
            return json.loads(text[first:last + 1])
        except json.JSONDecodeError:
            pass

    return None


def extract_findings(report: str, claims: dict = None,
                     evidence: dict = None) -> dict:
    """Extract structured findings from the auditor's response.

    Three sources of truth, in priority order:
      1. The model emitted AUDITOR ERROR → CRITICAL (auditor unavailable)
      2. The model emitted empty/None response → CRITICAL (silent failure)
      3. The model emitted valid JSON → use its discrepancies
      4. The deterministic comparator (this function) ALWAYS runs
         as a safety net and adds any missed findings.
    """
    findings = {
        "discrepancies": [],
        "verdict": "UNKNOWN",
        "summary": "",
        "model_emitted_json": False,
        "auditor_error": None,
    }

    # 1. Empty / None response = silent failure = CRITICAL
    if not report or not report.strip():
        findings["auditor_error"] = "Empty auditor response (silent failure)"
        findings["discrepancies"].append({
            "severity": "CRITICAL",
            "type": "auditor_silent_failure",
            "description": (
                "Auditor returned empty response. Governance gate cannot "
                "verify claims. Manual review required."
            ),
        })
        findings["verdict"] = "FAIL"
        findings["summary"] = "1 critical: auditor silent failure"
        return findings

    # 2. AUDITOR ERROR: prefix from auditor.py retry-exhaustion
    if report.strip().startswith("AUDITOR ERROR:"):
        findings["auditor_error"] = report.strip()
        findings["discrepancies"].append({
            "severity": "CRITICAL",
            "type": "auditor_unavailable",
            "description": report.strip(),
        })
        findings["verdict"] = "FAIL"
        findings["summary"] = "1 critical: auditor unavailable"
        return findings

    # 3. Try to parse structured JSON from the model
    model_json = _safe_load_json(report)
    if model_json and isinstance(model_json, dict):
        findings["model_emitted_json"] = True
        for d in model_json.get("discrepancies", []):
            if not isinstance(d, dict):
                continue
            severity = d.get("severity", "INFO").upper()
            if severity not in ("CRITICAL", "WARNING", "INFO"):
                severity = "INFO"
            findings["discrepancies"].append({
                "severity": severity,
                "type": "model_finding",
                "description": d.get("summary", ""),
                "claimed": d.get("claimed", ""),
                "actual": d.get("actual", ""),
            })

    # 4. Deterministic comparator — always runs, even if model emitted JSON
    if claims and evidence:
        _add_comparator_findings(findings, claims, evidence)

    # 5. Verdict from combined findings
    _finalize_verdict(findings)
    return findings


def _add_comparator_findings(findings: dict, claims: dict, evidence: dict):
    """The deterministic claim-vs-evidence check. Safety net."""

    # Future-dated diary entry — catches backdating
    claimed_date_str = claims.get("date", "")
    if claimed_date_str and claimed_date_str != "unknown":
        try:
            claimed = date.fromisoformat(claimed_date_str)
            today = date.today()
            if claimed > today:
                findings["discrepancies"].append({
                    "severity": "CRITICAL",
                    "type": "future_dated_diary",
                    "description": (
                        f"Diary claims date {claimed_date_str} but today is "
                        f"{today.isoformat()}. Future-dated entries are not "
                        f"permitted."
                    ),
                })
        except ValueError:
            pass

    # Test count mismatch
    claimed_tests = claims.get("test_counts", [{}])
    if claimed_tests and isinstance(claimed_tests[0], dict):
        claimed_n = claimed_tests[0].get("claimed_passing", 0)
    else:
        claimed_n = 0
    actual_tests = (evidence.get("tests", {}).get("passed", 0)
                    or evidence.get("actual_test_count", 0))
    if claimed_n and actual_tests and claimed_n != actual_tests:
        # Avoid duplicates if model already caught this
        if not _has_finding(findings, "Test count"):
            findings["discrepancies"].append({
                "severity": "CRITICAL",
                "type": "test_count_mismatch",
                "description": (
                    f"Test count: claimed {claimed_n}, actual {actual_tests}"
                ),
                "claimed": str(claimed_n),
                "actual": str(actual_tests),
            })

    # Tool count mismatch
    claimed_tools = claims.get("tools_count", 0)
    actual_tools = evidence.get("actual_tool_count", 0)
    if claimed_tools and actual_tools and claimed_tools != actual_tools:
        if not _has_finding(findings, "Tool count"):
            findings["discrepancies"].append({
                "severity": "CRITICAL",
                "type": "tool_count_mismatch",
                "description": (
                    f"Tool count: claimed {claimed_tools}, "
                    f"actual {actual_tools}"
                ),
                "claimed": str(claimed_tools),
                "actual": str(actual_tools),
            })

    # Date/mtime sanity (catches edits without re-saving)
    diary_timestamps = evidence.get("diary_timestamps", {})
    for fname, ts in diary_timestamps.items():
        if claimed_date_str and claimed_date_str in fname:
            mtime = ts.get("mtime", "")
            if claimed_date_str and claimed_date_str not in mtime:
                if not _has_finding(findings, "backdated"):
                    findings["discrepancies"].append({
                        "severity": "CRITICAL",
                        "type": "diary_backdated",
                        "description": (
                            f"Diary '{fname}' claims date "
                            f"{claimed_date_str} but file mtime is {mtime}"
                        ),
                    })

    # README state mismatches (warning, not critical)
    readme = evidence.get("readme_state", {})
    if readme.get("exists"):
        r_tests = readme.get("claimed_tests")
        r_tools = readme.get("claimed_tools")
        if r_tests and claimed_n and r_tests != claimed_n:
            findings["discrepancies"].append({
                "severity": "WARNING",
                "type": "readme_test_mismatch",
                "description": (
                    f"README claims {r_tests} tests, diary claims {claimed_n}"
                ),
            })
        if r_tools and claimed_tools and r_tools != claimed_tools:
            findings["discrepancies"].append({
                "severity": "WARNING",
                "type": "readme_tool_mismatch",
                "description": (
                    f"README claims {r_tools} tools, "
                    f"diary claims {claimed_tools}"
                ),
            })


def _has_finding(findings: dict, keyword: str) -> bool:
    """True if any existing finding description contains the keyword."""
    for d in findings["discrepancies"]:
        if keyword.lower() in d.get("description", "").lower():
            return True
    return False


def _finalize_verdict(findings: dict):
    """Compute verdict from the merged discrepancy list."""
    critical = sum(1 for d in findings["discrepancies"]
                   if d["severity"] == "CRITICAL")
    warnings = sum(1 for d in findings["discrepancies"]
                   if d["severity"] == "WARNING")

    if critical > 0:
        findings["verdict"] = "FAIL"
    elif warnings > 0:
        findings["verdict"] = "WARN"
    else:
        findings["verdict"] = "PASS"

    findings["summary"] = (
        f"{len(findings['discrepancies'])} discrepancies found "
        f"({critical} critical, {warnings} warnings)"
    )


def format_report(findings: dict) -> str:
    """Format findings into a clean text report."""
    lines = [
        "=" * 50,
        "GOVERNANCE AUDIT — STRUCTURED REPORT",
        "=" * 50,
        "",
        f"VERDICT: {findings['verdict']}",
        f"DISCREPANCIES: {findings['summary']}",
    ]
    if findings.get("auditor_error"):
        lines.append(f"AUDITOR ERROR: {findings['auditor_error']}")
    lines.append("")
    if findings["discrepancies"]:
        for i, d in enumerate(findings["discrepancies"], 1):
            lines.append(f"  {i}. [{d['severity']}] {d['description']}")
    else:
        lines.append("  (no discrepancies)")
    lines.append("")
    lines.append("=" * 50)
    return "\n".join(lines)


if __name__ == "__main__":
    report = sys.stdin.read()
    findings = extract_findings(report)
    print(format_report(findings))
    print("\n--- JSON ---")
    print(json.dumps(findings, indent=2))
