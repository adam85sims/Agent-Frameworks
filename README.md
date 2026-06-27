# Agent Frameworks

A collection of production-grade, highly reusable frameworks and tools for building and managing autonomous AI development agents. 

This repository contains components extracted from the **Hermes autonomous research-and-build experiment**:

1. **Hermes Automation Framework (`automation/`)** — A structured session state, work queue, and workflow guideline framework that helps AI agents execute long-running tasks autonomously and retain structural awareness across sessions.
2. **Governance Audit Harness (`governance/`)** — An independent compliance gate that collects codebase evidence (tests, file timestamps, tool count, README claims) and audits the agent's claimed changes using a local, lightweight LLM to verify correctness.
3. **Pattern Memory MCP Server (`pattern-memory/`)** — A Model Context Protocol (MCP) server that listens to developer-to-agent corrections, extracts behavioral rules, scores confidence, detects conflicts, and contextually injects rules to prevent repetitive AI errors.

---

## 📁 Repository Structure

```
Agent-Frameworks/
├── README.md                 # This file
├── automation/               # The Hermes Automation Framework templates & skills
│   ├── AGENTS.md             # Template guidelines for AI agent workflows
│   ├── TODO.md               # Template work queue for managing agent sprints
│   ├── .brain/               # Folder with templates for structural state tracking
│   │   ├── session.md.template
│   │   ├── map.json.template
│   │   └── memory.md.template
│   └── skills/               # Reusable workflow skills
│       ├── build/            # Build methodology guidelines
│       ├── model-routing/    # Optimization rules for task delegation
│       └── research/         # Problem discovery and research guidelines
│
├── governance/               # Configurable Compliance Audit Harness
│   ├── README.md             # Governance guide
│   ├── audit.py              # Main orchestrator script
│   ├── evidence.py           # Independent evidence collector (configurable)
│   ├── claims.py             # Markdown claim extractor
│   ├── auditor.py            # Local LLM API caller
│   ├── extract.py            # Post-processor & comparator safety net
│   ├── governance.yaml       # Project target configuration file
│   └── auditor.yaml          # LLM auditor model configuration file
│
└── pattern-memory/           # Reusable Pattern Memory MCP server code
    ├── README.md             # Setup guide and tool documentation
    ├── pyproject.toml        # Package configuration
    ├── server.py             # FastMCP server entry point
    ├── pattern_engine.py     # Core scoring, decay, and conflict resolution logic
    ├── storage.py            # Dual storage (SQLite + ChromaDB) layer
    ├── models.py             # Data structures and models
    ├── cli.py                # Command-line interface
    ├── wrapper.py            # Tool wrappers
    └── tests/                # Comprehensive unit/integration tests (68 tests)
```

---

## 🤖 1. The Hermes Automation Framework (`automation/`)

Designed to support autonomous software sprints (2–4 hours) while bridging context gaps between execution sessions.

*   **Work Queue (`TODO.md`)**: The single source of truth for the agent. It defines clear completion logic, priority, and exit conditions directly in the file structure to prevent the agent from stopping to ask "what next?".
*   **Structured Session State (`.brain/`)**:
    *   `session.md`: Tracks active goals, current status, and next moves.
    *   `map.json`: A structural index map of key files, entry points, schemas, and tools.
    *   `memory.md`: A log of architecture decisions and gotchas to prevent "context rot."
*   **Workflow Skills (`skills/`)**: Contains detailed Markdown instructions that define model routing criteria (e.g. Mimo for reasoning, DeepSeek for boilerplate), build methodologies, and problem discovery/research frameworks.

To apply this to a new workspace:
1. Copy the `automation/` folder contents into your workspace root.
2. Initialize `.brain/session.md`, `.brain/map.json`, and `.brain/memory.md` using the templates.
3. Add tasks to `TODO.md` and instruct your AI agent to follow the rules in `AGENTS.md`.

---

## ⚖️ 2. The Governance Audit Harness (`governance/`)

An automated compliance gate that verifies agent-stated output before check-in. It collects objective evidence from the workspace (via `evidence.py`), parses agent claims from markdown diaries (via `claims.py`), and uses a local LLM to run an audit.

*   **Config-Driven**: Specify your target folders, README, test commands, and files in `governance.yaml` to run it on any project.
*   **Deterministic Safety Net**: A Python comparator cross-checks critical figures (like test counts or tool counts) in `extract.py` to prevent LLM hallucinations.
*   **Loud Failures**: Auditor unavailable or empty output is flagged as `CRITICAL`, blocking progress.

See the [governance/README.md](file:///home/adam/Documents/Dev/Agent-Frameworks/governance/README.md) for configuration instructions.

---

## 🧠 3. Pattern Memory MCP Server (`pattern-memory/`)

A production-ready MCP server that implicitly learns developer preferences and corrections, saving them to sqlite and ChromaDB.

*   **Dual Storage**:SQLite handles structured metadata and timestamps; ChromaDB handles semantic vector searches for context-aware injection.
*   **Safeguards**: Confidence decay (`run_decay`), conflict detection (`check_conflicts`), and an auto-confirmation ceiling (`0.7`) ensuring silence alone never fully validates a pattern.
*   **Consolidated Tools**: 13 FastMCP tools for recording corrections, checking conflicts, resolving opposing patterns, and checking action rules.

See the [pattern-memory/README.md](file:///home/adam/Documents/Dev/Agent-Frameworks/pattern-memory/README.md) for setup and tools reference.
