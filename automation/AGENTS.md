# Agent Guide & Protocol

> An autonomous research-and-build project template. The agent discovers real-world problems, researches them deeply, designs solutions, and builds working software using a structured workflow and model routing.

**No deadline.** Spend real time considering and iterating. Quality over speed. One-week review cycle.

## Project Structure

```
Project-Root/
├── AGENTS.md              # This file — agent configuration
├── TODO.md                 # Work queue (source of truth for sessions)
├── skills/                 # Reusable workflows
│   ├── model-routing/     # When to use which model
│   ├── research/          # Research methodology
│   └── build/             # Build methodology
├── research/              # Research documents (RESEARCH.md files)
├── design/                # Design documents (DESIGN.md files)
├── src/                   # Source code
├── docs/                  # Documentation
├── updates/               # Daily diary entries (MANDATORY)
│   └── YYYY-MM-DD.md      # One file per day
├── governance/            # Audit harness (governance/audit.py)
│   └── reports/          # Audit reports from each session
└── .brain/                # Protocol files for structural awareness
    ├── map.json           # Codebase structural map
    ├── session.md         # Active session state
    └── memory.md          # Decision log (lessons learned)
```

## Key Constraints

- **No deadline** — take the time needed for quality work
- **One-week review** — after 7 days, review progress and adjust
- **Daily diary** — write to `updates/YYYY-MM-DD.md` every day
- **Subagents allowed** — delegate freely using model routing

## Model Routing Rules

**MANDATORY:** Route tasks to the optimal model based on the matrix below. Do NOT guess — follow the rules.

| Task Type | Model Category / Examples | Reason |
|-----------|--------------------------|--------|
| Research & Analysis | High-reasoning (e.g., Gemini 3.5 Pro / Claude 3.5 Sonnet) | Better reasoning, synthesis, pattern recognition |
| Problem Discovery | High-reasoning | Needs to connect disparate data points |
| Architecture Design | High-reasoning | Systems thinking, tradeoff analysis |
| Code Review | High-reasoning | Catches subtle issues, vision helps |
| Debugging | High-reasoning | Root cause analysis requires reasoning |
| Complex Algorithms | High-reasoning | Reasoning depth |
| Writing (docs, README) | High-reasoning | Better prose quality |
| Scaffolding | Fast / Cost-efficient (e.g., Gemini 3.5 Flash / DeepSeek V4) | Fast, doesn't overthink boilerplate |
| CRUD / API stubs | Fast / Cost-efficient | Speed wins, clear spec |
| Test stubs | Fast / Cost-efficient | Mechanical, well-patterned |
| Simple UI components | Fast / Cost-efficient | Template-driven |
| File structure setup | Fast / Cost-efficient | Convention over configuration |
| Data processing | Fast / Cost-efficient | Straightforward transforms |
| Integration glue | Fast / Cost-efficient | Connecting known pieces |

### Delegation Protocol

When delegating to a different model:
1. **Provide complete context** — file paths, current state, expected output
2. **Be specific** — exact endpoints, data shapes, function signatures
3. **Include examples** — show what the output should look like
4. **Set model override** in delegation call
5. **Always review output** — every delegation gets a review by a high-reasoning model before acceptance

### Workflow Pattern

```
Research (Reasoning Model) → Design (Reasoning Model) → Scaffold (Fast Model) → Review (Reasoning Model)
                                                                                  ↓
                                                                  Fix (Fast Model) ← Iterate
                                                                                  ↓
                                                                  Refine (Reasoning Model) → Ship
```

## Memory Management

### Active Memory (ChromaDB / VectorDB)
- Store research findings with tags: `research`, `problem-domain`, `source`
- Store design decisions with tags: `design`, `architecture`, `decision`
- Store build progress with tags: `build`, `milestone`, `shipped`
- Search before writing — avoid duplicating past research

### Passive Memory (AGENTS.md + skills)
- Update AGENTS.md when conventions change
- Create skills after completing complex workflows (5+ tool calls)
- Prune stale entries — if a fact is >7 days old, it belongs in the vector database, not active memory

### Memory Pruning
- Periodically review memory entries
- Move aged research to the vector database
- Remove outdated progress logs
- Keep only active decisions and preferences

## Work Queue (TODO.md)

**Core principle:** The agent works through a persistent TODO queue. The queue is the source of truth.

See `TODO.md` in the project root. Format:
- `[ ]` = pending item
- `[x]` = completed item
- Items in **Pending** are done top-to-bottom
- Items in **Blocked** need user input — stop, flag, move on
- Items in **Done** stay for history

### Exit conditions — STOP when ANY are true

1. TODO.md Pending section is empty (all done)
2. 3+ items completed this session (diminishing returns)
3. Audit shows CRITICAL discrepancies (fix first, then stop)
4. Blocker — item needs user input (mark blocked, stop)
5. Context >60% used (stop cleanly, next session continues)

### Adding work

The agent discovers new tasks while doing existing ones. Rules:
- Max 2 new items per session
- Add to the END of Pending, not the top
- Items should be concrete and actionable
- Items discovered from review go at the top of Pending

## Governance Integration

**Every session runs through governance.** The harness is at `governance/`.

### How it works

1. **Session does work** — writes code, docs, design, updates TODO.md
2. **Session runs audit:**
   ```bash
   python3 governance/audit.py . --output governance/reports/
   ```
3. **Audit collects evidence independently:**
   - Runs tests
   - Stats all source files for modification times
   - Counts actual MCP tool decorators (if applicable)
   - Parses diary dates and compares to file modification times
4. **Auditor model verifies claims against evidence**
5. **Post-processing extracts structured findings**

### Severity tiers

- **CRITICAL** — tests failing, false claims, backdated entries
  → Must fix before proceeding
- **WARNING** — count mismatches, missing files
  → Should fix, but not blocking
- **INFO** — internal inconsistencies, minor drift
  → Log and move on

### Hard rules

- If audit verdict is FAIL with CRITICAL issues, **do not finalize the session diary**.
- If you can't get the audit to pass, **flag for the user**.
- The audit is not optional. It's the verification of correctness.
- **CRITICAL always wins** — if audit finds a CRITICAL, fix it before anything else, even if you've already completed other items this session.

## Research-to-Release Framework

### Phase 1: Breadth (Research)
- Cast wide net across chosen problem domain
- Use browser tools for news, papers, community forums
- Store all findings in vector DB with proper tags
- Write `research/RESEARCH.md` with citations

### Phase 2: Synthesis (Analysis)
- Identify patterns across research
- Narrow to specific, tractable problem
- Validate problem exists (not already well-solved)
- Write problem statement with evidence

### Phase 3: Design (Planning)
- Write `design/DESIGN.md` with:
  - User personas
  - Solution architecture
  - Tech stack decisions
  - Data model
  - API design
  - UI/UX flow
- Get review before proceeding

### Phase 4: Build (Execution)
- Scaffold with fast model (fast structure)
- Core logic with reasoning model (complex reasoning)
- **Run governance audit before marking features complete**
- Test continuously

### Phase 5: Iterate
- Gather feedback (if live)
- Fix issues
- Add features
- **Re-audit after every significant change**
- Document changes

## Quality Gates

Before marking anything as "done":
- [ ] Code reviewed by reasoning model
- [ ] Tests pass (verified by test runner, not claimed)
- [ ] Documentation updated
- [ ] **Governance audit passes (VERDICT: PASS or WARN)**
- [ ] Vector DB/Memory updated with decisions
- [ ] No stale references in code

## Sanity Check Protocol

**If you're stuck, STOP and flag.** Don't spiral.

| Condition | Action |
|-----------|--------|
| 3 hours, zero new insights | Stop researching, write what you have, flag `[STUCK]` |
| Same sources repeating | Stop, pivot to synthesis or flag for review |
| Same task >2 hours, no progress | Step back, re-anchor on the main question |
| Heavy decision (stack choice, pivot) | Flag `[NEEDS_REVIEW]` in session log before acting |
| Audit keeps failing | Stop. The code is wrong, not the audit. Fix the code. |
