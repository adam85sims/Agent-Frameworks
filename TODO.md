# Agent-Frameworks — Reusable Framework TODO

> Goal: Make every module in this repo a drop-in component that works in ANY project,
> regardless of stack, directory layout, or AI agent platform.

---

## Phase 0: Foundation — Shared Infrastructure

Everything else depends on having a common base.

### P0.1 — Shared Config System
- [ ] Create `common/config.py` with layered config loading:
  1. Built-in safe defaults
  2. Project-level `agent-frameworks.yaml` (overrides defaults)
  3. Environment variable overrides (highest priority)
- [ ] Support YAML and `.env` files
- [ ] Provide `get_config(module_name)` so governance/, pattern-memory/,
      and automation/ each get their own section from one config file
- [ ] Remove all hardcoded paths from every module (governance defaults,
      LM Studio URLs, ChromaDB paths, etc.)
- [ ] Document the config schema in `common/CONFIG-SCHEMA.md`

### P0.2 — Shared Logging
- [ ] Create `common/logging.py` with a consistent logger setup:
  - Module prefix (e.g., `[governance]`, `[pattern-memory]`)
  - Configurable verbosity via config or env var (`AGENT_FW_LOG_LEVEL`)
  - Structured output option for machine consumption
  - Human-readable default for terminal use
- [ ] Replace all `print(..., file=sys.stderr)` calls across modules
      with the shared logger

### P0.3 — Package Structure
- [ ] Create top-level `pyproject.toml` for the monorepo:
  - Package name: `agent-frameworks`
  - Entry points for CLI tools (governance audit, pattern-memory, etc.)
  - Optional dependency groups: `[governance]`, `[pattern-memory]`, `[all]`
- [ ] Create `common/__init__.py` with version and shared exports
- [ ] Ensure each module (governance/, pattern-memory/, automation/)
      can also be used standalone if copied without the shared base
      (graceful degradation with warnings)

### P0.4 — Shared Data Models
- [ ] Create `common/models.py` with dataclasses for:
  - `AuditResult` (verdict, discrepancies, evidence summary)
  - `Discrepancy` (severity, type, description, claimed, actual)
  - `Evidence` (tests, timestamps, tool count, source files)
  - `Claim` (date, test counts, tool count, features, files)
  - `Pattern` (for pattern-memory interop if needed in future)
- [ ] All modules use these models internally; serialize to/from dict
      for JSON boundaries

---

## Phase 1: Governance Decoupling

The governance module is closest to production-ready but tightly coupled
to pattern-memory's directory layout and LM Studio specifically.

### P1.1 — Generic Defaults
- [ ] Change `evidence.py` defaults from:
  ```
  src_dir: "src/pattern-memory"
  mcp_server_file: "src/pattern-memory/server.py"
  test_dir: "src/pattern-memory/tests"
  ```
  To generic:
  ```
  src_dir: "src"
  readme_path: "README.md"
  mcp_server_file: null          # optional, skip tool counting if null
  diary_dir: "updates"
  test_dir: "tests"
  test_command: ["python3", "-m", "pytest", "tests/", "-v", "--tb=short"]
  test_cwd: "."
  source_file_pattern: "**/*.py"
  ```
- [ ] Update governance/README.md examples to show generic project config
- [ ] Remove legacy fallbacks to `updates-for-adam` (that was Hermes-specific)
- [ ] Add a `governance init` subcommand that scaffolds a `governance/`
      directory with default configs in any project root

### P1.2 — Configurable LLM Backend
- [ ] In `auditor.py`, replace hardcoded `LM_STUDIO_URL` and `LMS` path
      with config-driven values:
  ```yaml
  # in auditor.yaml
  backend:
    type: "openai-compatible"     # or "ollama", "llama-cpp", "vllm"
    url: "http://localhost:1234/v1/chat/completions"
    model_load_command: null      # optional: shell command to load model
    model_list_command: null      # optional: shell command to list models
    health_check: null            # optional: endpoint to ping
  ```
- [ ] Implement backend adapters:
  - `OpenAICompatibleBackend` — works with LM Studio, vLLM, LiteLLM,
    any OpenAI-compatible API
  - `OllamaBackend` — uses Ollama's native API (`/api/chat`)
  - `LlamaCppBackend` — uses llama.cpp's `--server` endpoint
  - `NoBackend` — skip LLM audit, use only deterministic comparator
- [ ] Pre-flight check should use the configured backend's list command,
      not assume `lms ls --json`
- [ ] Model loading should use the configured backend's load command,
      or skip if the backend doesn't support explicit loading (e.g.,
      Ollama loads on first request)

### P1.3 — Flexible Claims Extraction
- [ ] Make `claims.py` extensible with custom claim extractors:
  ```yaml
  # in governance.yaml
  claim_extractors:
    test_counts:
      pattern: "(\\d+)\\s*/\\s*(\\d+)\\s*(?:tests?|passing)"
      type: "count_pair"
    tool_counts:
      pattern: "(\\d+)\\s*\\w*\\s*(?:MCP\\s*)?tools?"
      type: "single_count"
    # Projects can add their own:
    custom_metric:
      pattern: "(\\d+)\\s*requests?/sec"
      type: "single_count"
      field: "performance_claims"
  ```
- [ ] Support multiple diary formats (not just `YYYY-MM-DD.md`):
  ```yaml
  diary:
    dir: "updates"
    naming: "date"              # or "sequential", "custom"
    date_format: "%Y-%m-%d"     # strftime format
  ```
- [ ] Add a `claims extract` CLI subcommand for debugging:
  ```
  python -m governance claims extract updates/2026-06-27.md --json
  ```

### P1.4 — Governance as a Library
- [ ] Expose a clean Python API:
  ```python
  from governance import run_audit
  
  result = run_audit(
      project_root=".",
      config_path="governance/governance.yaml",
      auditor_config_path="governance/auditor.yaml",
  )
  
  if result.verdict == "FAIL":
      for d in result.discrepancies:
          if d.severity == "CRITICAL":
              print(f"BLOCKED: {d.description}")
  ```
- [ ] Keep the CLI (`python3 governance/audit.py .`) as a thin wrapper
      around the library API

### P1.5 — Deterministic Comparator Expansion
- [ ] Add more built-in comparator checks in `extract.py`:
  - File existence checks (claimed files actually exist)
  - Import validity (claimed imports resolve)
  - API endpoint checks (claimed routes are registered)
- [ ] Make comparator checks pluggable:
  ```yaml
  # in governance.yaml
  comparators:
    - type: "test_count_mismatch"     # built-in
    - type: "tool_count_mismatch"     # built-in
    - type: "file_existence"          # built-in
    - type: "custom_regex"            # user-defined
      pattern: "(\\d+)\\s*users?"
      evidence_key: "actual_user_count"
      severity: "WARNING"
  ```

---

## Phase 2: Pattern Memory — Config & Packaging

Pattern-memory is already solid. Main work is making it config-driven
and installable alongside the framework.

### P2.1 — Configurable Storage
- [ ] Replace hardcoded ChromaDB and SQLite paths with config:
  ```yaml
  # in agent-frameworks.yaml
  pattern_memory:
    sqlite_path: "~/.agent-frameworks/pattern-memory.db"
    chroma_path: "~/.agent-frameworks/chromadb"
    singleton_pid: "~/.agent-frameworks/pattern-memory.pid"
  ```
- [ ] Support `memory_db_url` env var for containerized deployments
- [ ] Add graceful fallback if ChromaDB is unavailable (SQLite-only mode
      with a warning that semantic search is degraded)

### P2.2 — MCP Config Generation
- [ ] Add a `pattern-memory configure` command that generates the MCP
      server config for detected agent platforms:
  ```
  Detected agents:
    - Claude Desktop     -> writes to ~/.config/claude/claude_desktop_config.json
    - Hermes Agent       -> writes to ~/.hermes/config.yaml (mcpServers section)
    - OpenCode           -> writes to ~/.config/opencode/opencode.jsonc
    - Cursor             -> writes to .cursor/mcp.json
    - Custom             -> prints config snippet for manual insertion
  ```
- [ ] Backup existing config before overwriting
- [ ] Show diff before applying changes (interactive confirmation)

### P2.3 — Testing Improvements
- [ ] Add integration test that starts the MCP server and calls all 13
      tools in sequence (currently only 1 test does this)
- [ ] Add test for SQLite-only fallback mode
- [ ] Add test for config-driven storage paths
- [ ] Ensure tests work without ChromaDB installed (mocked mode)

---

## Phase 3: Automation — Platform-Agnostic

### P3.1 — Model Routing by Capability
- [ ] Replace hardcoded model names in model-routing/SKILL.md with a
      capability-based config:
  ```yaml
  # in agent-frameworks.yaml
  model_routing:
    reasoning:
      models:
        - provider: "opencode-go"
          model: "mimo-v2.5"
        - provider: "anthropic"
          model: "claude-sonnet-4"
      use_for:
        - "research"
        - "architecture"
        - "code_review"
        - "debugging"
        - "complex_algorithms"
        - "documentation"
    speed:
      models:
        - provider: "opencode-go"
          model: "deepseek-v4-flash"
        - provider: "openrouter"
          model: "google/gemini-2.5-flash"
      use_for:
        - "scaffolding"
        - "crud"
        - "test_stubs"
        - "simple_ui"
        - "boilerplate"
  ```
- [ ] Update AGENTS.md to reference the config file, not inline model
      names
- [ ] Add a `routing list` command to show current model assignments

### P3.2 — Improved .brain Templates
- [ ] Expand `session.md.template`:
  ```markdown
  # Session State
  
  - **Started:** [ISO timestamp]
  - **Current Goal:** [Active goal]
  - **Status:** [in-progress / testing / blocked / review-needed]
  - **Context Used:** [percentage estimate]
  
  ## Active Tasks
  1. [Task description] — [status]
  
  ## Blockers
  - [Blocker description] — needs: [what's needed]
  
  ## Recent Decisions
  - [Decision made this session and reasoning]
  ```
- [ ] Expand `map.json.template` with schema documentation:
  ```json
  {
    "_schema": "Project structural map. Updated by agent as it explores.",
    "_fields": {
      "entry_points": "List of main entry point files",
      "key_components": "Map of component name -> path",
      "database_schema": "Database locations and table definitions",
      "api_endpoints": "API base URL and route list",
      "config_files": "Configuration file locations",
      "test_commands": "How to run tests"
    },
    "entry_points": ["src/main.py"],
    "key_components": {},
    "database_schema": {},
    "api_endpoints": {},
    "config_files": {},
    "test_commands": {}
  }
  ```
- [ ] Expand `memory.md.template` with structured categories:
  ```markdown
  # Memory Log (Lessons Learned)
  
  ## Architecture Decisions
  | Date | Decision | Reasoning | Revisit? |
  |------|----------|-----------|----------|
  
  ## Gotchas & Pitfalls
  | Date | Issue | Root Cause | Fix |
  |------|-------|------------|-----|
  
  ## Performance Notes
  | Date | Observation | Metric | Action Taken |
  |------|-------------|--------|--------------|
  
  ## User Preferences
  | Preference | Context | First Noted |
  |------------|---------|-------------|
  ```

### P3.3 — Exit Conditions Refinement
- [ ] Make exit conditions configurable per project:
  ```yaml
  # in agent-frameworks.yaml
  automation:
    exit_conditions:
      max_items_per_session: 3
      context_usage_limit: 0.6
      max_consecutive_failures: 3
      require_governance_pass: true
    work_queue:
      max_new_items_per_session: 2
      self_seed_when_near_empty: true
  ```

---

## Phase 4: Install Script

This is the "make it just work" layer. A single script that detects the
environment and sets up everything needed.

### P4.1 — `setup.sh` or `install.py`
- [ ] Create `setup.py` (or `setup.sh`) at the repo root that:
  
  **Detects the environment:**
  - Python version (3.11+ required)
  - Available package managers (pip, pipx, uv)
  - Running AI agent platforms (Claude Desktop, Hermes, OpenCode, Cursor)
  - LLM backends (LM Studio, Ollama, llama.cpp, vLLM)
  - Container runtime (Podman, Docker) for ChromaDB
  
  **Installs the framework:**
  ```
  pip install -e ".[all]"          # or uv/pipx equivalent
  ```
  
  **Sets up databases:**
  - Initialize SQLite database for pattern-memory
  - Start or configure ChromaDB (detect if already running)
  - For rootless Podman: set up ChromaDB container with proper networking
  
  **Configures MCP integration:**
  - Detect which agent platform(s) are installed
  - Generate MCP server config for each detected platform
  - Offer to install into each detected platform (with confirmation)
  
  **Configures LLM backend:**
  - Detect available backends (LM Studio, Ollama, etc.)
  - Generate `auditor.yaml` with detected backend URL
  - Verify the configured model is available (or offer to download)
  
  **Creates project config:**
  - Generate `agent-frameworks.yaml` with detected settings
  - Scaffold `governance/` directory if not present
  - Scaffold `.brain/` directory from templates if not present

### P4.2 — `setup.py` Subcommands
- [ ] `setup.py init` — Full interactive setup for new projects
- [ ] `setup.py check` — Verify everything is configured and working:
  - Python deps installed?
  - ChromaDB reachable?
  - LLM backend responding?
  - MCP config valid for detected agents?
  - Governance configs present and valid?
- [ ] `setup.py doctor` — Diagnose and fix common problems:
  - ChromaDB not running -> start it
  - MCP config missing -> regenerate it
  - LLM model not loaded -> load it
  - SQLite DB missing -> initialize it
- [ ] `setup.py uninstall` — Clean removal of configs and data

### P4.3 — Platform-Specific Detection
- [ ] **Claude Desktop:**
  - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
  - Linux: `~/.config/claude/claude_desktop_config.json`
  - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- [ ] **Hermes Agent:**
  - `~/.hermes/config.yaml` (mcpServers section)
- [ ] **OpenCode:**
  - `~/.config/opencode/opencode.jsonc`
- [ ] **Cursor:**
  - `.cursor/mcp.json` (project-local)
  - `~/.cursor/mcp.json` (global)
- [ ] **Continue.dev:**
  - `~/.continue/config.yaml`
- [ ] **Custom/Unknown:**
  - Print the JSON snippet and tell the user where to paste it

### P4.4 — ChromaDB Setup (Rootless Podman)
- [ ] Detect if ChromaDB is already running on configured port
- [ ] If not, offer to start via Podman:
  ```
  podman run -d \
    --name agent-fw-chromadb \
    -p 8000:8000 \
    -v agent-fw-chroma:/chroma/chroma \
    chromadb/chroma:latest
  ```
- [ ] For non-container environments, support direct ChromaDB install
  ```
  pip install chromadb
  # and run as embedded client
  ```
- [ ] Verify connectivity after setup
- [ ] Document manual setup as fallback

---

## Phase 5: Documentation & Examples

### P5.1 — Main README Rewrite
- [ ] Rewrite `README.md` for framework consumers, not Hermes developers:
  - "What problem does this solve?"
  - "Quick start" (3 commands to get running)
  - "Architecture overview" (diagram of the three modules)
  - "Configuration reference" (link to CONFIG-SCHEMA.md)
  - "CLI reference" (all available commands)
  - "Contributing" (how to extend with new modules)

### P5.2 — Module READMEs
- [ ] Update governance/README.md with generic examples
- [ ] Update pattern-memory/README.md with multi-platform MCP configs
- [ ] Create automation/README.md (currently missing — only AGENTS.md)

### P5.3 — Example Projects
- [ ] Create `examples/` directory with:
  - `examples/minimal/` — Governance only, minimal project
  - `examples/full-stack/` — All three modules, web app project
  - `examples/mcp-only/` — Pattern-memory with Claude Desktop
  - Each example has its own README showing the setup

### P5.4 — API Documentation
- [ ] Document the Python API for each module (what functions are
      public, what they accept, what they return)
- [ ] Add type stubs or ensure all public functions have type hints

---

## Phase 6: Polish & Hardening

### P6.1 — Error Handling Audit
- [ ] Review every module for consistent error patterns:
  - Config missing -> clear error message with fix instructions
  - Backend unavailable -> retry logic + user notification
  - Database locked -> graceful degradation
  - Permission denied -> helpful path suggestions
- [ ] Add `--verbose` flag to all CLI commands for debugging

### P6.2 — Testing
- [ ] Add integration tests that exercise the full pipeline:
  - governance: collect evidence -> extract claims -> audit -> report
  - pattern-memory: record -> retrieve -> rate -> inject
  - automation: template init -> session state -> exit conditions
- [ ] Add CI config (GitHub Actions or similar) for the test suite
- [ ] Test on Python 3.11, 3.12, 3.13, 3.14

### P6.3 — Security Review
- [ ] Audit config loading for injection risks (YAML safe_load is good,
      but verify no eval/exec paths)
- [ ] Audit LLM prompts for prompt injection via claim text
- [ ] Ensure no secrets end up in config files or logs
- [ ] Add `.gitignore` entries for sensitive paths

### P6.4 — Performance
- [ ] Profile governance audit on large projects (1000+ files)
- [ ] Ensure ChromaDB doesn't leak handles (the self-healing fix in
      pattern-memory is good, but verify the pattern holds)
- [ ] Add caching for repeated evidence collection within a session

---

## Dependency Order

```
Phase 0 (Foundation)
  └─> Phase 1 (Governance Decoupling)
  └─> Phase 2 (Pattern Memory Config)
  └─> Phase 3 (Automation Platform-Agnostic)
Phase 1 + Phase 2 + Phase 3
  └─> Phase 4 (Install Script) — needs all modules config-driven first
Phase 4
  └─> Phase 5 (Documentation) — docs should reflect final architecture
  └─> Phase 6 (Polish) — hardening comes after the structure is stable
```

Phases 1-3 can be done in parallel after Phase 0 is complete.
Phase 4 depends on 1-3 being done. Phases 5-6 come last.

---

## Success Criteria

When this TODO is complete:

1. `setup.py init` in any Python project detects the environment and
   configures all three modules in under 60 seconds
2. `governance audit` works on any project with a valid governance.yaml,
   regardless of directory structure or LLM backend
3. Pattern-memory MCP server works with Claude Desktop, Hermes, OpenCode,
   Cursor, or any MCP-compatible client
4. Model routing works by capability class — swap model names in config,
   not in code
5. All three modules can be used independently (copy just governance/
   without needing pattern-memory/ or automation/)
6. A new user can read the README and be running in 5 minutes
