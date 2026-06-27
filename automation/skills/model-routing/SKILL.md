---
name: model-routing
description: "Routes tasks to optimal models based on strengths. Mimo V2.5 for research, planning, review, complex reasoning. DeepSeek V4 Flash for scaffolding, boilerplate, fast coding. Always review delegations."
---

# Model Routing

> Treat models like specialized workers. Mimo thinks, DeepSeek builds. Every delegation gets reviewed.

## Model Strengths

| Model | Strengths | Use For |
|-------|-----------|---------|
| Mimo V2.5 | Reasoning, planning, vision, review, prose | Research, design, code review, debugging, complex logic |
| DeepSeek V4 Flash | Fast coding, no overthinking | Scaffolding, CRUD, boilerplate, tests, simple UI |

## Routing Rules

### → Mimo V2.5 (Research & Thinking)
- Problem discovery and analysis
- Architecture design
- Code review and debugging
- Complex algorithms
- Writing documentation
- Synthesizing research
- Design documents

### → DeepSeek V4 Flash (Building & Speed)
- Project scaffolding
- API stubs and CRUD endpoints
- Test scaffolding
- Simple UI components
- File structure setup
- Data transforms
- Integration glue

### → Either (Context-Dependent)
- Core implementation: simple → DeepSeek, complex → Mimo
- Data processing: straightforward → DeepSeek, novel → Mimo

## Delegation Protocol

```python
# When delegating to DeepSeek:
delegate_task(
    goal="Build a FastAPI project with /api/problems endpoint...",
    context="Complete spec including data models, file paths...",
    model={"provider": "opencode-go", "model": "deepseek-v4-flash"}
)

# When delegating to Mimo:
delegate_task(
    goal="Review this code for security issues...",
    context="Full file contents and specific concerns...",
    model={"provider": "opencode-go", "model": "mimo-v2.5"}
)
```

## Review Rule

**Every delegation output gets reviewed before acceptance.** No exceptions.

When reviewing:
1. Check against the original spec
2. Run tests if applicable
3. Verify no regressions
4. Check for edge cases
5. Accept or send back with specific fixes

## Governance Review (for all builds)

After any delegation that produces code, documentation, or design:

1. **Run the governance audit:**
   ```bash
   python3 ~/Documents/Hermes-Project/governance/audit.py ~/Documents/Hermes-Project --output ~/Documents/Hermes-Project/governance/reports/
   ```

2. **Check the verdict:**
   - PASS: work is real, proceed
   - WARN: minor issues, address them
   - FAIL: stop, fix the underlying problem

3. **Never accept delegation output that fails the audit.** The delegation
   claimed to do something — verify it actually did.

## Gotchas

- **Don't let DeepSeek do research** — it'll generate plausible-sounding but shallow analysis
- **Don't let Mimo scaffold** — it'll overthink the boilerplate and waste time
- **Always provide complete context** — subagents have no memory of your conversation
- **Model overrides are per-delegation** — they don't persist across calls
- **Trust but verify** — the governance audit is the verification layer
