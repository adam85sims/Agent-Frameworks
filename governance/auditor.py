#!/usr/bin/env python3
"""Governance Auditor — calls a small local LLM via LM Studio to verify claims.

Replaces the Gemma-4-12b implementation that got stuck in reasoning loops
(see archive/governance-reports/gemma-era-2026-06-24/ for the evidence).

Key design changes (2026-06-24 swap):
  1. Config-driven model name (auditor.yaml). No more hardcoded strings.
  2. Pre-flight existence check — we know the model file is on disk
     before we send a request. Failures become loud, not silent.
  3. Retry on empty/None response — Gemma produced empty raw_report
     5 times in 19 runs. We now retry up to N times with backoff.
  4. Never unload — Adam's 2026-06-24 direction. Keeps models warm
     in VRAM between audits.
  5. Direct JSON-out prompt — no chain-of-thought preamble. The
     audit task is a structured compare, not a reasoning task.
  6. Optional escalation model for ambiguous cases.
"""

import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

# Lazy import for yaml so this module is importable without PyYAML
# (it's a stdlib-plus dep in the project, but we degrade gracefully).
try:
    import yaml  # type: ignore
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
LMS = str(Path.home() / ".lmstudio" / "bin" / "lms")
LMSTUDIO_MODELS_DIR = Path.home() / ".lmstudio" / "models"
CONFIG_PATH = Path(__file__).parent / "auditor.yaml"


# ─── Configuration loading ────────────────────────────────────────

def load_config(path: Path = CONFIG_PATH) -> dict:
    """Load auditor.yaml. Falls back to safe defaults if PyYAML missing."""
    if not path.exists():
        return _default_config()

    if not HAS_YAML:
        print(
            "  WARNING: PyYAML not installed; using built-in defaults. "
            "Install with: pip install pyyaml",
            file=sys.stderr,
        )
        return _default_config()

    with path.open() as f:
        return yaml.safe_load(f)


def _default_config() -> dict:
    """Fallback if config file missing."""
    return {
        "primary": {
            "model": "ibm/granite-4.1-3b",
            "context_length": 8192,
            "temperature": 0.0,
            "max_tokens": 1024,
            "gpu": "max",
            "expect_on_disk": True,
        },
        "escalation": None,
        "keep_resident": True,
        "retry": {"max_attempts": 3, "backoff_seconds": 5},
        "on_exhausted_retries": "critical",
    }


# ─── Pre-flight checks ────────────────────────────────────────────

def is_model_on_disk(model_key: str) -> bool:
    """Check if a model with this key is downloaded in LM Studio.

    Authoritative source: `lms ls --json` returns the canonical modelKey
    for everything LM Studio knows about. We use it instead of guessing
    directory names because lms get <alias> downloads to a directory
    whose name doesn't always match the alias (e.g. the alias
    `mistralai/ministral-3-8b` is stored under
    `lmstudio-community/Ministral-3-8B-Instruct-2512-GGUF/`).
    """
    try:
        result = subprocess.run(
            [LMS, "ls", "--json", "--llm"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return False
        import json as _json
        models = _json.loads(result.stdout)
        for m in models:
            if m.get("modelKey") == model_key:
                return True
            # Also accept if the alias matches the indexedModelIdentifier
            if m.get("indexedModelIdentifier") == model_key:
                return True
        return False
    except Exception as e:
        print(f"  Pre-flight check failed: {e}", file=sys.stderr)
        # Fall back to directory check
        candidate = LMSTUDIO_MODELS_DIR / model_key
        return candidate.exists()


def is_model_loaded(model_key: str) -> bool:
    """Check if model is currently in VRAM via lms ps."""
    try:
        result = subprocess.run(
            [LMS, "ps"], capture_output=True, text=True, timeout=10
        )
        return model_key in result.stdout
    except Exception:
        return False


def load_model(model_key: str, context_length: int, gpu: str = "max",
               timeout: int = 120) -> bool:
    """Load model into VRAM. Returns True if loaded successfully."""
    if is_model_loaded(model_key):
        return True

    print(f"  Loading {model_key} into VRAM...", file=sys.stderr)
    try:
        result = subprocess.run(
            [LMS, "load", model_key,
             "--context-length", str(context_length),
             "--gpu", gpu],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode == 0 or "loaded successfully" in result.stdout.lower():
            print(f"  Loaded {model_key}.", file=sys.stderr)
            return True
        print(f"  Load failed: {result.stdout[-300:]}", file=sys.stderr)
        return False
    except subprocess.TimeoutExpired:
        print(f"  Load timed out after {timeout}s.", file=sys.stderr)
        return False


# ─── Audit prompt — direct JSON out, no chain-of-thought ──────────

# This prompt is deliberately minimal. The audit task is a structured
# compare: "does this claim match this evidence?" The Gemma-era prompt
# asked for "Reasoning" and "VERDICT" in a specific format, which
# triggered reasoning loops in chain-of-thought-tuned models.
#
# For small instruction-tuned models (Granite, Ministral) we want:
#   - No preamble
#   - No "let me check"
#   - Direct JSON output matching the schema
#   - Concise discrepancy list (or empty list)
#
# The output JSON is what extract.py parses. The model's job is just
# to enumerate the diffs.

AUDIT_PROMPT = """You are an audit engine. Compare CLAIMS to EVIDENCE.

Output ONLY a JSON object with this exact schema. No prose, no preamble, no markdown fence:

{
  "claims_total": <integer>,
  "verified": <integer>,
  "discrepancies": [
    {
      "severity": "CRITICAL" | "WARNING" | "INFO",
      "summary": "<one sentence>",
      "claimed": "<exact value or short quote from CLAIMS>",
      "actual": "<exact value or short quote from EVIDENCE>"
    }
  ],
  "verdict": "PASS" | "FAIL" | "WARN"
}

Rules:
- CRITICAL: false claims, tests that claim to pass but failed, backdated entries, contradictory values.
- WARNING: count mismatches, missing files referenced in claims, internal inconsistencies.
- INFO: minor drift, wording differences, optional claims with no evidence.
- "verified" = claims_total minus discrepancies that are CRITICAL or WARNING.
- If the diary claims a future date, that is CRITICAL.
- If a claimed test count does not match the actual passed test count, that is CRITICAL.
- If a claimed tool count does not match the actual decorator count, that is CRITICAL.
- Treat path differences (e.g. "server.py" vs "src/pattern-memory/server.py") as INFO unless the file does not exist.
- Output ONLY the JSON object, nothing else."""


# ─── The audit call ───────────────────────────────────────────────

def call_model(model_key: str, claims: dict, evidence: dict,
               temperature: float, max_tokens: int,
               context_length: int) -> Optional[str]:
    """One attempt at calling the model. Returns content string or None."""
    if not load_model(model_key, context_length):
        return None

    user_content = (
        "CLAIMS (from diary entry):\n"
        f"{json.dumps(claims, indent=2, default=str)}\n\n"
        "EVIDENCE (independently collected):\n"
        f"{json.dumps(evidence, indent=2, default=str)}"
    )

    payload = {
        "model": model_key,
        "messages": [
            {"role": "system", "content": AUDIT_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        req = urllib.request.Request(
            LM_STUDIO_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            message = result["choices"][0]["message"]
            content = (message.get("content") or "").strip()
            return content if content else None
    except urllib.error.URLError as e:
        print(f"  Network error: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  Error: {e}", file=sys.stderr)
        return None


def audit(claims: dict, evidence: dict, config: dict = None,
          use_escalation: bool = False) -> str:
    """Run audit. Returns the raw model output as a string.

    Empty/None responses are retried up to config['retry']['max_attempts'].
    On exhaustion, returns a string with an explicit AUDITOR ERROR marker
    that extract.py must surface as CRITICAL.
    """
    cfg = config or load_config()
    role = "escalation" if use_escalation else "primary"
    section = cfg.get(role) or cfg["primary"]
    retries = cfg.get("retry", {}).get("max_attempts", 3)
    backoff = cfg.get("retry", {}).get("backoff_seconds", 5)

    model_key = section["model"]

    # Pre-flight: model must exist on disk
    if section.get("expect_on_disk", True) and not is_model_on_disk(model_key):
        return (
            f"AUDITOR ERROR: Model '{model_key}' not found on disk. "
            f"Download with: lms get {model_key}@q4_k_m"
        )

    last_result: Optional[str] = None
    for attempt in range(1, retries + 1):
        print(f"  [{role}] attempt {attempt}/{retries}...", file=sys.stderr)
        last_result = call_model(
            model_key, claims, evidence,
            temperature=section.get("temperature", 0.0),
            max_tokens=section.get("max_tokens", 1024),
            context_length=section.get("context_length", 8192),
        )
        if last_result:
            return last_result
        if attempt < retries:
            print(f"  Empty response, retrying in {backoff}s...",
                  file=sys.stderr)
            time.sleep(backoff)

    # All retries exhausted
    return (
        f"AUDITOR ERROR: {model_key} returned no content after {retries} "
        f"attempts. Check LM Studio is running, model is loaded, and "
        f"VRAM is available."
    )


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: auditor.py <claims.json> <evidence.json> [--escalation]")
        sys.exit(1)

    escalation = "--escalation" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    claims = json.loads(Path(args[0]).read_text())
    evidence = json.loads(Path(args[1]).read_text())

    cfg = load_config()
    result = audit(claims, evidence, cfg, use_escalation=escalation)
    print(result)
