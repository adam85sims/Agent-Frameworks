#!/usr/bin/env python3
"""
HERMES GOVERNANCE HARNESS
=========================
Independent audit of autonomous agent output.

Flow:
  1. Collect evidence (independent observation)
  2. Extract claims (from diary entry)
  3. Send both to Gemma-4-12b (airgapped auditor)
  4. Store report + return verdict

Usage:
  python audit.py <project_root> [--diary YYYY-MM-DD] [--output reports/]
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add governance dir to path
sys.path.insert(0, str(Path(__file__).parent))

from claims import extract_claims
from evidence import collect_evidence
from auditor import audit
from extract import extract_findings, format_report


def run_audit(project_root: str, diary_date: str = None, output_dir: str = None) -> dict:
    """Run a full governance audit."""
    root = Path(project_root)

    # Step 1: Collect evidence FIRST (before reading any claims)
    print("[1/5] Collecting evidence...", file=sys.stderr)
    evidence = collect_evidence(str(root))

    # Step 2: Find the diary entry
    from evidence import load_governance_config
    gov_cfg = load_governance_config(root)
    diary_dir_name = gov_cfg.get("diary_dir", "updates")
    diary_dir = root / diary_dir_name
    if not diary_dir.exists() and diary_dir_name == "updates":
        # Fallback to legacy updates-for-adam
        diary_dir = root / "updates-for-adam"
    archive_dir = root / "archive" / "diaries"

    if diary_date:
        diary_path = diary_dir / f"{diary_date}.md"
        if not diary_path.exists():
            diary_path = archive_dir / f"{diary_date}.md"
        if not diary_path.exists():
            print(f"ERROR: No diary entry for {diary_date} found in active or archive", file=sys.stderr)
            sys.exit(1)
    else:
        # Use the most recent diary entry (active first, then archive)
        diaries = sorted(diary_dir.glob("*.md"))
        if not diaries:
            diaries = sorted(archive_dir.glob("*.md"))
        if not diaries:
            print("ERROR: No diary entries found (active or archive)", file=sys.stderr)
            sys.exit(1)
        diary_path = diaries[-1]

    print(f"[2/5] Extracting claims from {diary_path.name}...", file=sys.stderr)
    claims = extract_claims(str(diary_path))

    # Step 3: Send to auditor
    from auditor import load_config as _load_auditor_config
    auditor_cfg = _load_auditor_config()
    auditor_model = auditor_cfg.get("primary", {}).get("model", "unknown")
    print(f"[3/5] Sending to {auditor_model} auditor...", file=sys.stderr)
    raw_report = audit(claims, evidence, config=auditor_cfg)

    # Step 4: Post-process to extract structured findings
    print("[4/5] Extracting findings...", file=sys.stderr)
    findings = extract_findings(raw_report, claims, evidence)

    # Escalation: if primary model failed OR didn't emit valid JSON,
    # try the escalation model and merge findings.
    if (not findings.get("model_emitted_json")
            or findings.get("auditor_error")):
        esc_model = auditor_cfg.get("escalation")
        if esc_model:
            print(
                f"[4/5] Primary model failed/unparseable, "
                f"escalating to {esc_model.get('model')}...",
                file=sys.stderr,
            )
            esc_raw = audit(claims, evidence, config=auditor_cfg,
                            use_escalation=True)
            esc_findings = extract_findings(esc_raw, claims, evidence)
            if esc_findings.get("model_emitted_json"):
                # Merge: prefer escalation findings when it parsed
                findings = esc_findings
                raw_report = (
                    f"--- PRIMARY FAILED ---\n{raw_report}\n\n"
                    f"--- ESCALATION ({esc_model.get('model')}) ---\n"
                    f"{esc_raw}"
                )
            # If escalation also failed, keep primary findings

    # Step 5: Store results
    print("[5/5] Storing results...", file=sys.stderr)
    result = {
        "audit_timestamp": datetime.now().isoformat(),
        "diary_file": str(diary_path),
        "auditor_model": auditor_model,
        "claims": claims,
        "evidence_summary": {
            "tests_passed": evidence["tests"]["passed"],
            "tests_failed": evidence["tests"]["failed"],
            "tests_total": evidence["tests"]["total"],
            "actual_tool_count": evidence["actual_tool_count"],
            "actual_test_count": evidence["actual_test_count"],
            "diary_timestamps": evidence["diary_timestamps"],
        },
        "findings": findings,
        "raw_report": raw_report,
    }

    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        report_path = out / f"audit-{timestamp}.json"
        report_path.write_text(json.dumps(result, indent=2))
        print(f"Report saved to {report_path}", file=sys.stderr)

        # Also save a human-readable version
        txt_path = out / f"audit-{timestamp}.txt"
        txt_path.write_text(f"""GOVERNANCE AUDIT REPORT
======================
Date: {result['audit_timestamp']}
Diary: {result['diary_file']}
Auditor: {result.get('auditor_model', 'unknown')}

EVIDENCE SUMMARY
  Tests: {evidence['tests']['passed']}/{evidence['tests']['total']} passed, {evidence['tests']['failed']} failed
  MCP Tools (actual): {evidence['actual_tool_count']}
  Test Functions (actual): {evidence['actual_test_count']}

{format_report(findings)}

RAW AUDITOR OUTPUT
{raw_report}
""")
        print(f"Human-readable: {txt_path}", file=sys.stderr)

    return result


def main():
    parser = argparse.ArgumentParser(description="Hermes Governance Auditor")
    parser.add_argument("project_root", help="Path to the Hermes Project root")
    parser.add_argument("--diary", help="Diary date to audit (YYYY-MM-DD)", default=None)
    parser.add_argument("--output", help="Output directory for reports", default=None)
    parser.add_argument("--json", action="store_true", help="Output JSON to stdout")

    args = parser.parse_args()

    result = run_audit(args.project_root, args.diary, args.output)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(format_report(result["findings"]))


if __name__ == "__main__":
    main()
