#!/usr/bin/env python3
"""Collect independent evidence about a project's state.

This runs BEFORE any claims are read — pure observation.
Configurable via governance.yaml.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    import yaml  # type: ignore
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def load_governance_config(root: Path) -> dict:
    """Load governance.yaml. Falls back to safe defaults if missing or PyYAML unavailable."""
    cfg_path = root / "governance" / "governance.yaml"
    if not cfg_path.exists():
        # Try root directory in case of execution from nested dirs
        cfg_path = root / "governance.yaml"
        
    defaults = {
        "src_dir": "src/pattern-memory",
        "readme_path": "README.md",
        "mcp_server_file": "src/pattern-memory/server.py",
        "diary_dir": "updates",
        "test_dir": "src/pattern-memory/tests",
        "test_command": [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        "test_cwd": "src/pattern-memory",
        "source_file_pattern": "**/*.py"
    }

    if not cfg_path.exists():
        return defaults

    if not HAS_YAML:
        print(
            "  WARNING: PyYAML not installed; using built-in defaults. "
            "Install with: pip install pyyaml",
            file=sys.stderr,
        )
        return defaults

    try:
        with cfg_path.open() as f:
            user_cfg = yaml.safe_load(f) or {}
            # Merge defaults with user config
            for key, val in user_cfg.items():
                defaults[key] = val
            return defaults
    except Exception as e:
        print(f"  Error loading governance.yaml: {e}", file=sys.stderr)
        return defaults


def collect_evidence(project_root: str) -> dict:
    """Gather all verifiable facts about the project state."""
    root = Path(project_root)
    config = load_governance_config(root)

    evidence = {
        "collected_at": datetime.now().isoformat(),
        "project_root": str(root),
        "tests": run_tests(root, config),
        "file_timestamps": get_file_timestamps(root, config),
        "actual_tool_count": count_mcp_tools(root, config),
        "actual_test_count": count_test_functions(root, config),
        "readme_state": analyze_readme(root, config),
        "diary_timestamps": get_diary_timestamps(root, config),
        "source_files": list_source_files(root, config),
    }
    return evidence


def run_tests(root: Path, config: dict) -> dict:
    """Run the full test suite and capture results."""
    test_dir = root / config.get("test_dir", "src/pattern-memory/tests")
    if not test_dir.exists():
        return {"status": "no_test_dir", "passed": 0, "failed": 0, "errors": []}

    test_cmd = config.get("test_command", [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"])
    cwd_path = root / config.get("test_cwd", "src/pattern-memory")

    # Run tests
    try:
        result = subprocess.run(
            test_cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(cwd_path),
        )
        passed = 0
        failed = 0
        errors = []

        for line in result.stdout.split("\n"):
            if " PASSED" in line:
                passed += 1
            elif " FAILED" in line:
                failed += 1
                # Extract test name
                m = re.search(r"(.+?)::(\S+)\s+FAILED", line)
                if m:
                    errors.append(f"{m.group(1)}::{m.group(2)}")

        return {
            "exit_code": result.returncode,
            "passed": passed,
            "failed": failed,
            "total": passed + failed,
            "errors": errors,
            "output": result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout,
        }
    except Exception as e:
        return {
            "exit_code": -999,
            "passed": 0,
            "failed": 0,
            "total": 0,
            "errors": [str(e)],
            "output": f"Error running tests: {e}"
        }


def get_file_timestamps(root: Path, config: dict) -> dict:
    """Get modification times for all source files."""
    timestamps = {}
    src_dir = root / config.get("src_dir", "src/pattern-memory")
    pattern = config.get("source_file_pattern", "**/*.py")
    if src_dir.exists():
        # Handle case where pattern is recursive or simple glob
        glob_iter = src_dir.rglob(pattern.replace("**/", "")) if pattern.startswith("**/") else src_dir.glob(pattern)
        for f in sorted(glob_iter):
            if "__pycache__" in str(f) or ".git" in str(f):
                continue
            if f.is_dir():
                continue
            stat = f.stat()
            timestamps[str(f.relative_to(root))] = {
                "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "ctime": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "size": stat.st_size,
            }
    return timestamps


def count_mcp_tools(root: Path, config: dict) -> int:
    """Count actual MCP tool definitions in the server file."""
    server_py = root / config.get("mcp_server_file", "src/pattern-memory/server.py")
    if not server_py.exists():
        return 0

    content = server_py.read_text()
    # Count @mcp.tool() decorators
    return len(re.findall(r"@mcp\.tool\(\)", content))


def count_test_functions(root: Path, config: dict) -> int:
    """Count actual test functions in test files."""
    test_dir = root / config.get("test_dir", "src/pattern-memory/tests")
    if not test_dir.exists():
        return 0

    count = 0
    # Scan files matching test_*.py
    for f in test_dir.rglob("test_*.py"):
        if f.is_dir():
            continue
        content = f.read_text()
        count += len(re.findall(r"^def test_", content, re.MULTILINE))
    return count


def analyze_readme(root: Path, config: dict) -> dict:
    """Check what the README claims vs reality."""
    readme = root / config.get("readme_path", "README.md")
    if not readme.exists():
        return {"exists": False}

    content = readme.read_text()
    # Extract claimed test count
    test_claim = re.search(r"(\d+)/\d+\s*(?:tests?|passing)", content)
    # Extract claimed tool count (first match in main content)
    tool_claim = re.search(r"(\d+)\s*\w*\s*(?:MCP\s*)?tools?", content)

    return {
        "exists": True,
        "claimed_tests": int(test_claim.group(1)) if test_claim else None,
        "claimed_tools": int(tool_claim.group(1)) if tool_claim else None,
        "size": len(content),
    }


def get_diary_timestamps(root: Path, config: dict) -> dict:
    """Get file system timestamps for all diary entries."""
    diary_dir = root / config.get("diary_dir", "updates")
    if not diary_dir.exists():
        # Fallback to updates-for-adam
        diary_dir = root / "updates-for-adam"
    if not diary_dir.exists():
        return {}

    timestamps = {}
    for f in sorted(diary_dir.glob("*.md")):
        stat = f.stat()
        timestamps[f.name] = {
            "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "ctime": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "size": stat.st_size,
        }
    return timestamps


def list_source_files(root: Path, config: dict) -> list:
    """List all source files."""
    src_dir = root / config.get("src_dir", "src/pattern-memory")
    pattern = config.get("source_file_pattern", "**/*.py")
    if not src_dir.exists():
        return []

    files = []
    glob_iter = src_dir.rglob(pattern.replace("**/", "")) if pattern.startswith("**/") else src_dir.glob(pattern)
    for f in sorted(glob_iter):
        if "__pycache__" in str(f) or ".git" in str(f):
            continue
        if f.is_dir():
            continue
        files.append({
            "path": str(f.relative_to(root)),
            "size": f.stat().st_size,
            "mtime": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
        })
    return files


if __name__ == "__main__":
    project_root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    evidence = collect_evidence(project_root)
    print(json.dumps(evidence, indent=2))
