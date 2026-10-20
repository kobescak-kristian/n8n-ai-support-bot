# Eval results: n8n AI support bot (Q-123)

Gate and metric definitions: `evals/eval_config.yaml`. Every run is
appended here, pass or fail; entries are never edited or deleted. A run
counts only when its results artifact is committed and the runner
exited with code 0.

Entry format: date | config version | model + version | dataset version
(generator commit, hold-out SHA-256) | score per metric | gate verdict |
miss analysis | newly broken cases | changed variables vs previous entry | cost.

## Entries

### visible-1 — 2026-10-20 05:42, development run (not gated)

- Config: evals/eval_config.yaml v1 · workflows 84bbee9 · model claude-sonnet-5-5 (effort low) + text-embedding-3-small · dataset tests/cases/visible.json (97 cases, SHA-256 c5a9c15f...) · runner exit 0, 563 s.
- Scores: rate 53/55 (one run only; the gate needs 3 runs and the hold-out); critical failures 0 (25 critical cases, CF checks on every reply); code metrics all 1.0: log_complete 99/99, handoff_complete 30/30, dont_know_offer 15/15, citation_integrity 43/43, human_mode_silent 1/1, agent_reply_exact 4/4, close_returns 1/1, whatsapp_adapter 7/7, outage_handled 5/5, index_public_only 1/1.
- Result: development run, no verdict (single run, no hold-out).
- Misses: R3-02 (instalments + price): the price article A19 was not in the top-5 retrieved, Claude answered the instalment part and routed dont_know. R9-03 (complaint, threat of reviews): best similarity 0.19 < floor 0.20, so the floor shortcut answered "I don't know" without calling Claude; the complaint was never seen. Both are workflow causes.
- Changed vs previous entry: first entry.
- Cost: $0.357 AI cost for the run (Claude + embeddings, from logged tokens); seconds per AI reply median 3.1, 90th percentile 4.2.
