# Agent Frameworks

**Reusable frameworks for building and managing autonomous AI agents.**

Drop-in modules for governance auditing, pattern memory, and workflow automation.
Config-driven, stack-agnostic, and designed to work with any AI agent platform
(Claude Desktop, Hermes, OpenCode, Cursor, etc.) and any LLM backend (LM Studio,
Ollama, vLLM, OpenAI-compatible APIs).

## Quickstart

```bash
# Install
pip install -e ".[all]"

# Detect your environment (agents, LLMs, containers)
agent-fw-setup detect

# Initialize a new project
agent-fw-setup init

# Verify everything's configured
agent-fw-setup check

# Auto-fix common issues
agent-fw-setup doctor
```

## What's Inside

```
agent-frameworks/
├── common/           Shared infrastructure (config, logging, models, setup CLI)
├── governance/       Verify AI agent claims against objective evidence
├── pattern-memory/   Learn from corrections, inject into future sessions
├── automation/       Model routing, session state, work queue management
├── tests/            126 tests across all modules
└── pattern-memory/   Independent package with its own pyproject.toml
```

### Modules

**common/** — Foundation layer shared by all modules

- `config.py` — Layered config: built-in defaults -> `agent-frameworks.yaml` -> env vars
- `logging.py` — Structured logging with module prefixes (`[governance]`, `[pattern-memory]`)
- `models.py` — Data models: `AuditResult`, `Discrepancy`, `Evidence`, `Claim`, `Severity`, `Verdict`
- `setup_cli.py` — Environment detection and project initialization CLI

**governance/** — Verify AI agent claims against objective evidence

- `audit.py` — Orchestrates the full audit pipeline, returns `AuditResult`
- `evidence.py` — Independently collects: test results, file timestamps, MCP tool counts
- `claims.py` — Parses agent diary entries for claims (extensible via `custom_patterns`)
- `auditor.py` — Config-driven LLM backends (OpenAI-compatible, Ollama, none)
- `extract.py` — Extracts structured findings from auditor output + deterministic comparators

**pattern-memory/** — Learn from corrections, inject into future sessions

- `server.py` — MCP server (13 tools) for recording and retrieving patterns
- `storage.py` — SQLite + ChromaDB with graceful SQLite-only fallback
- `cli.py` — CLI interface for pattern recording and retrieval
- `wrapper.py` — Session wrapper for automatic correction capture
- `mcp_config.py` — Detects installed agents and generates MCP configs
- `config.py` — Config-driven paths with graceful `common.config` fallback

**automation/** — Config-driven model routing and session management

- `model_routing.py` — Routes tasks to optimal models by capability tier
- `session.py` — Manages `.brain/` directory (session.md, memory.md, map.json)
- `work_queue.py` — TODO.md queue with configurable exit conditions

## Configuration

All modules read from a single `agent-frameworks.yaml` in your project root:

```yaml
governance:
  src_dir: "src"
  readme_path: "README.md"
  test_command: ["python3", "-m", "pytest", "tests/", "-v", "--tb=short"]
  test_cwd: "."
  source_file_pattern: "**/*.py"

pattern_memory:
  sqlite_path: "~/.agent-frameworks/pattern-memory.db"
  chroma_path: "http://127.0.0.1:8000"

automation:
  model_routing:
    reasoning:
      models:
        - provider: "openai-compatible"
          model: "claude-sonnet-4"
      use_for: ["research", "architecture", "code_review", "debugging"]
    speed:
      models:
        - provider: "openai-compatible"
          model: "deepseek-v4-flash"
      use_for: ["scaffolding", "crud", "boilerplate"]
  exit_conditions:
    max_items_per_session: 3
    context_usage_limit: 0.6
    require_governance_pass: true
```

### Environment Variable Overrides

Any config key can be overridden via env vars using the `AGENT_FW_<SECTION>_<KEY>` convention:

```bash
AGENT_FW_GOVERNANCE_SRC_DIR=lib
AGENT_FW_PATTERN_MEMORY_CHROMA_PATH=http://localhost:9000
AGENT_FW_AUTOMATION_EXIT_CONDITIONS_MAX_ITEMS_PER_SESSION=5
```

## Usage Examples

### Governance Audit

```python
from governance import run_audit

result = run_audit(
    project_root=".",
    output_dir="governance/reports/",
)

print(f"Verdict: {result.verdict}")
for d in result.discrepancies:
    print(f"  [{d.severity}] {d.description}")
```

### Pattern Memory (MCP)

Add to your agent's MCP config:

```json
{
  "pattern-memory": {
    "command": "python3",
    "args": ["/path/to/agent-frameworks/pattern-memory/server.py"]
  }
}
```

Or use the CLI:

```bash
# Record a correction
python3 pattern-memory/cli.py record \\
  --session "2026-06-27" \\
  --category "testing" \\
  --correction "Use caplog instead of capsys for log assertions" \\
  --context "capsys captures stdout, not logging"

# Retrieve patterns
python3 pattern-memory/cli.py find --query "log assertions"
```

### Automation: Model Routing

```python
from automation import ModelRouter

router = ModelRouter()

# Route by task type — returns the best model from config
model = router.route("research")
# -> {"provider": "openai-compatible", "model": "claude-sonnet-4"}

model = router.route("scaffolding")
# -> {"provider": "openai-compatible", "model": "deepseek-v4-flash"}

# List all configured task types
tasks = router.list_tasks()
# -> {"research": "reasoning", "scaffolding": "speed", ...}
```

### Automation: Session State

```python
from automation import SessionState

session = SessionState()
session.start("Build authentication system")
session.add_decision("Used JWT over sessions", "Stateless, scales better")
session.add_gotcha("Token expiry not tested", "Add test for refresh flow")
session.update_map(
    entry_points=["src/main.py"],
    key_components={"auth": "src/auth/"},
    test_commands=["pytest tests/test_auth.py"],
)
session.save()
# Writes .brain/session.md, .brain/memory.md, .brain/map.json
```

### Automation: Work Queue

```python
from automation import WorkQueue

queue = WorkQueue()
queue.load()  # Reads TODO.md

item = queue.next_item()
if item:
    # ... do the work ...
    queue.complete(item.id)
    queue.save()  # Writes back to TODO.md

# Check exit conditions
reason = queue.should_exit(context_usage=0.65)
if reason:
    print(f"Time to stop: {reason}")
    # "queue_empty" | "max_items_completed" | "context_usage_high" | "has_blocked_items"
```

## CLI Reference

### agent-fw-setup

```
agent-fw-setup init      Create config, governance/, .brain/, TODO.md
agent-fw-setup check     Verify everything is configured
agent-fw-setup doctor    Diagnose and auto-fix common problems
agent-fw-setup detect    Show detected agents, LLMs, and containers
agent-fw-setup uninstall Remove agent-frameworks configs and data
```

Options:
```
--root DIR    Project root directory (default: current directory)
--yes, -y     Skip confirmation prompts
--force       Overwrite existing config (init)
--version     Show version
```

### agent-fw-audit

```bash
agent-fw-audit . --output governance/reports/
```

## Architecture

```
                    agent-frameworks.yaml
                            |
            +---------------+---------------+
            |               |               |
      governance/     pattern-memory/    automation/
            |               |               |
            +-------+-------+-------+-------+
                    |               |
                common/config    common/models
                    |               |
                common/logging ---+
```

**Design Principles:**

1. **Config-driven** — No hardcoded paths, model names, or backend assumptions
2. **Graceful degradation** — PyYAML optional, ChromaDB optional, common optional
3. **Independently usable** — Each module works standalone or as part of the framework
4. **Pattern-memory independently packageable** — Has its own `pyproject.toml`
5. **Convention: `AGENT_FW_<SECTION>_<KEY>`** for env var overrides

## Requirements

- Python 3.11+
- Optional: PyYAML (for YAML config files)
- Optional: ChromaDB (for pattern-memory vector search)
- Optional: MCP SDK (for pattern-memory MCP server)

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Testing

126 tests across all modules:

```bash
# Framework tests
pytest tests/ -v

# Pattern-memory independent tests
cd pattern-memory && pytest tests/ -v
```

## License

MIT