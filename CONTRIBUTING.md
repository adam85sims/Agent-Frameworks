# Contributing to Agent Frameworks

## Development Setup

```bash
# Clone and install in development mode
git clone <repo-url>
cd agent-frameworks
pip install -e ".[dev]"

# Run tests
pytest tests/ -v --tb=short

# Run pattern-memory tests independently
cd pattern-memory
pytest tests/ -v --tb=short
```

## Project Structure

```
agent-frameworks/
├── common/              Shared infrastructure
│   ├── __init__.py      Public API exports
│   ├── config.py        Layered config (defaults -> yaml -> env)
│   ├── logging.py       Structured logging with module prefixes
│   ├── models.py        Data models (AuditResult, Discrepancy, etc.)
│   └── setup_cli.py     Setup/diagnostics CLI
├── governance/          Audit framework
│   ├── __init__.py      Public API exports
│   ├── audit.py         Orchestrates audit pipeline
│   ├── evidence.py      Independently collects evidence
│   ├── claims.py        Parses diary claims (extensible)
│   ├── auditor.py       Config-driven LLM backends
│   └── extract.py       Extracts findings from auditor output
├── pattern-memory/      MCP server for learning from corrections
│   ├── server.py        13 MCP tools
│   ├── storage.py       SQLite + ChromaDB (graceful fallback)
│   ├── cli.py           CLI interface
│   ├── wrapper.py       Session wrapper
│   ├── mcp_config.py    Agent detection + MCP config generation
│   ├── config.py        Config-driven paths
│   └── pyproject.toml   Independent package
├── automation/          Workflow automation
│   ├── __init__.py      Public API exports
│   ├── model_routing.py Config-driven task-to-model routing
│   ├── session.py       .brain/ state management
│   └── work_queue.py    TODO.md queue with exit conditions
├── tests/               126 tests for all modules
├── pyproject.toml       Top-level package
├── TODO.md              Project roadmap
└── README.md            User documentation
```

## Design Principles

1. **Config-driven, not hardcoded.**

   No hardcoded paths, model names, URLs, or assumptions. Everything flows
   from `agent-frameworks.yaml` or environment variables. If you find yourself
   typing a literal path or model name in a `.py` file, it should probably be
   configurable instead.

2. **Graceful degradation at every boundary.**

   - PyYAML not installed? Config falls back to defaults + env vars only.
   - ChromaDB not running? Pattern-memory falls back to SQLite-only mode.
   - `common` package not available? Pattern-memory config falls back to its
     own built-in defaults.
   - No LLM backend configured? Governator auditor uses the `none` backend
     (deterministic comparators only, no LLM calls).

3. **Each module is independently usable.**

   Copy `governance/` into any project and it works. Copy `pattern-memory/`
   and it works. The `common` package enhances them but is not required.

4. **Pattern-memory is independently packageable.**

   It has its own `pyproject.toml` and can be published as a standalone
   package. The `common.config` integration uses `try/except` imports.

5. **Env var convention: `AGENT_FW_<SECTION>_<KEY>`**

   All environment overrides follow this pattern. Multi-word keys use
   underscores: `AGENT_FW_GOVERNANCE_SRC_DIR`.

6. **TDD workflow.**

   Write failing tests first, implement to green, then refactor. Every
   module has comprehensive tests (see test counts below).

## Test Counts

| Module | Tests | File |
|--------|-------|------|
| common/config | 14 | tests/test_config.py |
| common/logging | 10 | tests/test_logging.py |
| common/models | 21 | tests/test_models.py |
| governance | 33 | tests/test_governance.py |
| automation | 30 | tests/test_automation.py |
| setup_cli | 18 | tests/test_setup.py |
| **Framework total** | **126** | |
| pattern-memory | 86 | pattern-memory/tests/ |

## Coding Conventions

- **Comments:** Comment anything important — intentional design decisions,
  non-obvious behavior, tuning rationale, magic numbers and the reasoning
  behind them. "If it's not obvious, annotate it."

- **No hardcoded values:** Favor derived/algorithmic solutions over lookup
  tables or magic numbers. Key locations and designations should be
  configurable, not pinned to defaults.

- **Docstrings:** Every public class and function gets a docstring. Include
  a usage example for non-trivial APIs.

- **Type hints:** Use type hints on all function signatures. Python 3.11+
  syntax is fine (e.g., `list[str]` not `List[str]`).

- **Import order:** stdlib, third-party, local. One blank line between groups.

## Adding a New Module

1. Create the directory with an `__init__.py` that exports the public API
2. Add a config section to `agent-frameworks.yaml` (with defaults in the module)
3. Use `common.config.Config` to read config — never hardcode values
4. Write tests in `tests/test_<module>.py`
5. Add optional dependencies to `pyproject.toml` under `[project.optional-dependencies]`
6. Update `docs/api.md` with the new public API
7. Update `README.md` if the module changes the quickstart

## Git Workflow

- `main` branch for stable commits
- Each logical phase gets its own commit with a clear message
- Commit message format: `type: description` (e.g., `feat:`, `fix:`, `docs:`,
  `chore:`, `test:`)
- Don't push or rewrite history unless asked

## Running Tests

```bash
# Full framework test suite
pytest tests/ -v --tb=short

# Specific module
pytest tests/test_governance.py -v

# Pattern-memory (independent package)
cd pattern-memory && pytest tests/ -v
```

## Debugging Tips

- Set `AGENT_FW_LOG_LEVEL=DEBUG` to enable verbose logging
- Run `agent-fw-setup detect` to see what's detected in your environment
- Run `agent-fw-setup doctor` to auto-fix common config issues
- Check `agent-frameworks.yaml` for config typos
- Pattern-memory falls back to SQLite-only when ChromaDB is unavailable —
  check `~/.agent-frameworks/pattern-memory.db` for data

## Known Gotchas

- **PyYAML optional:** If PyYAML is not installed, only env vars override
  defaults. YAML config files are silently skipped (with a debug log message).
- **ChromaDB handles:** If ChromaDB connection drops, storage.py self-heals
  by recreating the collection. But if ChromaDB is down entirely, it falls
  back to SQLite-only mode.
- **MCP tool counting:** The regex `\s*` bridges newlines, which can match
  across line boundaries unexpectedly. Fixed by using `[^\S\n]` instead.
- **Empty dict truthiness:** `if claims and evidence:` skips when either is
  an empty dict (falsy). Use `is not None` checks instead.
- **Pyright and pytest:** Pyright may flag `item` as `Optional[WorkItem]`
  in test code after `next_item()`. This is a test-level concern, not a
  runtime bug — tests ensure items exist before calling `.id` on them.