---
name: research
description: "Research methodology for autonomous problem discovery. Casts wide net, synthesizes findings, identifies tractable problems. Uses ChromaDB for persistence, browser for discovery, crawl4ai for scraping."
---

# Research Methodology

> Find real problems. Understand them deeply. Prove they exist before building solutions.

## Research Process

### Phase 1: Breadth Scan
Cast a wide net across the problem domain:

1. **News & Current Events** — What are people struggling with right now?
2. **Community Forums** — Reddit, Hacker News, Stack Overflow, Twitter/X
3. **Academic Papers** — What's being researched but not yet built?
4. **Open Source** — What exists but is incomplete or poorly maintained?
5. **Competitor Analysis** — What commercial tools exist? What do they charge?
6. **Policy & Regulation** — What new laws/regulations create problems?

### Phase 2: Pattern Recognition
Across all findings, look for:

- **Recurring complaints** — Same problem mentioned in multiple places
- **Gap between need and solution** — People want X, nothing good exists
- **Price barriers** — Solutions exist but are too expensive
- **Complexity barriers** — Solutions exist but are too hard to use
- **Access barriers** — Solutions exist but aren't available everywhere

### Phase 3: Problem Selection
Criteria for choosing a problem to solve:

1. **Real** — Can cite multiple independent sources
2. **Tractable** — Can build a meaningful solution with available tools
3. **Not well-solved** — Existing solutions have clear gaps
4. **Impactful** — Helps real people, not just developers
5. **Buildable** — Can ship a working prototype, not just a concept

### Phase 4: Deep Dive
Once a problem is selected:

1. **Who is affected?** — Demographics, scale, geography
2. **What exists?** — Complete landscape of current solutions
3. **What's missing?** — Specific gaps in current solutions
4. **What would help?** — User research, pain points, desires
5. **What's the data?** — Numbers, statistics, evidence

## Storage Protocol

All research findings go to a vector database (e.g. ChromaDB):

```python
# Store a finding (example tool / script invocation)
python3 scripts/chroma_memory.py store \
  "Finding Title" \
  "Detailed description with context and source" \
  --tags "research,domain-topic,source-type"

# Search existing findings
python3 scripts/chroma_memory.py search "topic" --n 10

# Review recent findings
python3 scripts/chroma_memory.py recent --n 20
```

### Tag Conventions
- `research` — all research findings
- `problem-domain` — specific domain (e.g., `climate`, `education`, `housing`)
- `source-type` — `news`, `paper`, `forum`, `github`, `competitor`
- `finding` — specific discovery
- `synthesis` — pattern or insight from multiple findings
- `design` — design decisions
- `build` — build progress

## Output Format

Research culminates in `research/RESEARCH.md`:

```markdown
# [Problem Domain] — Research Report

## Executive Summary
[2-3 sentences: what we found, why it matters]

## Problem Statement
[Clear, evidence-backed statement of the problem]

## Evidence
### Finding 1
- Source: [URL/publication]
- Date: [when published]
- Key insight: [what we learned]
- ChromaDB ID: [for reference]

### Finding 2
...

## Landscape Analysis
### Existing Solutions
| Solution | What it does | Price | Gap |
|----------|-------------|-------|-----|
| ... | ... | ... | ... |

### What's Missing
[Synthesized gaps across all findings]

## Recommendation
[Which specific problem to solve and why]

## Next Steps
[Design phase outline]
```

## Gotchas

- **Cite everything** — never present research without sources
- **Distinguish facts from opinions** — label clearly
- **Check dates** — recent data > old data
- **Cross-reference** — one source is an anecdote, multiple sources are evidence
- **Store before writing** — ChromaDB first, document second (survives crashes)

## Sanity Check Protocol

**Autonomous research has failure modes.** Follow these rules to avoid them:

### Recursive Loop Detection
If any of these are true, STOP researching:
- Last 3 hours of browser activity yielded zero new insights
- Same 3 sources keep appearing in search results
- ChromaDB tags show >80% concentration in one narrow topic
- You've re-read the same document more than twice

**When detected:**
1. Stop all browser/search activity
2. Write what you have so far to `research/RESEARCH.md` (even if incomplete)
3. Log the situation to `research/HEARTLOG.md` with flag: `[STUCK]`
4. Wait for manual review — do NOT pivot autonomously

### Context Reset
If research feels stale or unfocused:
1. Clear active memory buffer (but keep ChromaDB — embeddings persist)
2. Re-read your `research/RESEARCH.md` to re-anchor
3. Ask: "What is the ONE question I'm trying to answer?"
4. If you can't answer that, flag for review

### Heavy Decision Gate
Before any of these actions, flag for manual review in HEARTLOG.md:
- Committing code to production
- Choosing a tech stack
- Pivoting to a different problem domain
- Deleting or archiving significant research
- Installing new system-level dependencies

**Flag format:** `[NEEDS_REVIEW] <description of decision and reasoning>`

### Time Limits
- **Research phase:** Max 4 hours continuous before forced pause
- **Build phase:** Max 6 hours continuous before forced pause
- **Any phase:** If you've been on the same task >2 hours with no progress, step back

When a time limit hits:
1. Log current state to HEARTLOG.md
2. Write/update `updates/` diary entry
3. Pause until next heartbeat or manual input
