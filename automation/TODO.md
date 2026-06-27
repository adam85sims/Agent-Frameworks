# Work Queue

> The agent works through this list top-to-bottom during each session.
> Pick the first unchecked item. Mark done when complete. Run governance audit.

## Rules

1. **Pick the first `[ ]` item** under "Pending" — do it, mark `[x]`, move to "Done"
2. **Max 2 new items per session** — only add tasks you discovered from doing other tasks
3. **Exit ONLY when ANY of these is true:**
   - Queue is empty (all items done or blocked)
   - Audit shows CRITICAL — fix first, then re-audit, then stop
   - Blocker hit (needs user input) — mark blocked with explanation, write diary, stop
   - 8+ items completed this session (excellent work — finalize and stop)
   - Cannot continue quality work (repeated failures, unavailable resources)
4. **After completing each item, IMMEDIATELY move to the next** — do not stop, summarize, or ask what to do next. You have hours of work ahead.
5. **New items go at the END of Pending** — unless you can argue they're higher priority
6. **Never mark something done without doing it** — the governance audit checks
7. **When the queue is near empty, self-seed** — find concrete issues in the codebase and add them. Only ask the user when the choice is between fundamentally different directions.

## Pending

- [ ] Initialize the project and setup codebase structure
- [ ] Write initial tests to verify the setup
- [ ] Implement the core application logic

## Done

(empty)

## Blocked

(empty)
