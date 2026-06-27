#!/usr/bin/env python3
"""Extract claims from a diary entry for audit verification.

Built-in extractors handle common patterns (test counts, tool counts, etc.).
Custom extractors can be added via the `custom_patterns` parameter.
"""

import re
import sys
from pathlib import Path
from typing import Optional

from common.logging import get_logger

logger = get_logger("governance.claims")


def extract_claims(diary_path: str, custom_patterns: dict = None) -> dict:
    """Parse a diary markdown file and extract verifiable claims.

    Args:
        diary_path: Path to the diary markdown file.
        custom_patterns: Optional dict of additional patterns to extract.
            Format: {"field_name": r"regex_pattern"}
            The regex should have one capture group for the value.

    Returns:
        Dictionary of extracted claims.
    """
    text = Path(diary_path).read_text()
    claims = {
        "file": str(diary_path),
        "date": extract_date(diary_path),
        "test_counts": extract_test_counts(text),
        "version": extract_version(text),
        "tools_count": extract_tools_count(text),
        "features": extract_features(text),
        "files_modified": extract_files_modified(text),
        "raw_sections": extract_key_sections(text),
    }

    # Apply custom extractors
    if custom_patterns:
        for field_name, pattern in custom_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                claims[field_name] = matches
                logger.debug("Custom extractor '%s' found %d matches", field_name, len(matches))

    return claims


def extract_date(path: str) -> str:
    """Extract date from filename like 2026-06-24.md."""
    match = re.search(r"(\d{4}-\d{2}-\d{2})", path)
    return match.group(1) if match else "unknown"


def extract_test_counts(text: str) -> list:
    """Extract all test count claims.

    Matches patterns like:
      - "53/53 tests"
      - "34/34 passing"
      - "20 tests passing"
      - "68/68 ✅"
    """
    claims = []
    # Match "N/N tests/passing/✅/ALL PASS"
    for m in re.finditer(
        r"(\d+)\s*/\s*(\d+)\s*(?:tests?|passing|✅|ALL PASS)", text, re.IGNORECASE
    ):
        claims.append({"claimed_passing": int(m.group(1)), "claimed_total": int(m.group(2))})
    # Match "N tests passing"
    for m in re.finditer(r"(\d+)\s+tests?\s+passing", text, re.IGNORECASE):
        claims.append({"claimed_passing": int(m.group(1)), "claimed_total": int(m.group(1))})
    return claims


def extract_version(text: str) -> str:
    """Extract version claim (e.g., v0.13.0)."""
    m = re.search(r"v(\d+\.\d+\.\d+)", text)
    return m.group(1) if m else "unknown"


def extract_tools_count(text: str) -> int:
    """Extract claimed MCP tool count (last mention = current state)."""
    matches = re.findall(r"(\d+)\s*\w*\s*(?:MCP\s*)?tools?", text, re.IGNORECASE)
    return int(matches[-1]) if matches else 0


def extract_features(text: str) -> list:
    """Extract feature names from bold bullet points."""
    features = []
    for m in re.finditer(r"^\s*[-*]\s+\*\*(.+?)\*\*", text, re.MULTILINE):
        features.append(m.group(1).strip())
    return features


def extract_files_modified(text: str) -> list:
    """Extract file modification claims from a "files modified" section."""
    files = []
    in_section = False
    for line in text.split("\n"):
        if "files modified" in line.lower():
            in_section = True
            continue
        if in_section:
            m = re.match(r"^\s*[-*]\s+`(.+?)`", line)
            if m:
                files.append(m.group(1))
            elif line.strip() and not line.startswith(" ") and not line.startswith("-"):
                break
    return files


def extract_key_sections(text: str) -> dict:
    """Extract key narrative sections (## headers) for context."""
    sections = {}
    current_section = None
    current_content = []

    for line in text.split("\n"):
        if line.startswith("## "):
            if current_section:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = line[3:].strip()
            current_content = []
        elif current_section:
            current_content.append(line)

    if current_section:
        sections[current_section] = "\n".join(current_content).strip()

    return sections


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: claims.py <diary_path>")
        sys.exit(1)

    import json
    claims = extract_claims(sys.argv[1])
    print(json.dumps(claims, indent=2))
