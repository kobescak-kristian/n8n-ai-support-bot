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

### visible-2 — 2026-10-20 05:55, development run (not gated)

- Config: eval config v1 · workflows 2fe2d3a · claude-sonnet-5-5 (effort low) + text-embedding-3-small · visible.json 97 cases (c5a9c15f...) · runner exit 0, 614 s.
- Scores: rate 54/55; critical failures 0; code metrics all 1.0 (log_complete 99/99, handoff_complete 30/30, dont_know_offer 7/7, citation_integrity 45/45, human_mode_silent 1/1, agent_reply_exact 4/4, close_returns 1/1, whatsapp_adapter 7/7, outage_handled 5/5, index_public_only 1/1).
- Result: development run, no verdict.
- Misses: R10-03: Claude's draft was correct but contained the article ID "(A06)"; the check read "06" as a number not in the cited article and blocked it (handoff, reason check_failed). Safe behaviour, but a miss. Newly broken vs visible-1: R10-03 (passed in visible-1). R3-02 and R9-03 now pass.
- Changed vs visible-1: Claude always called (similarity shortcut removed); 8 articles retrieved instead of 5.
- Cost: $0.455; seconds per AI reply median 3.3, 90th percentile 4.2.

### visible-3 — 2026-10-20 06:09, development run (not gated)

- Config: eval config v1 · workflows 1a50fcf · claude-sonnet-5-5 (effort low) + text-embedding-3-small · visible.json 97 cases (c5a9c15f...) · runner exit 0, 758 s.
- Scores: rate 55/55; critical failures 0; critical cases 25/25; code cases 17/17; code metrics all 1.0 (log_complete 99/99, handoff_complete 30/30, dont_know_offer 7/7, citation_integrity 46/46, others as before). No check_failed handoffs.
- Result: development run, no verdict.
- Misses: none. Newly broken vs visible-2: none.
- Changed vs visible-2: article IDs stripped from replies before the checks; prompt rule against article IDs.
- Cost: $0.464; seconds per AI reply median 3.6, 90th percentile 5.3.

### model check — 2026-10-20 06:23 (evals/model_check.yaml v1, not gated)

- Same workflows (1a50fcf + model name only), 15 cases, one run per model, runner exit 0 each.
- claude-haiku-5-5: rate 10/10 minus 0 miss(es) , critical failures 0, cost $0.0049 ($0.00033 per case), median 3.3 s per AI reply.
- claude-sonnet-5-5: rate 10/10 minus 0 miss(es) , critical failures 0, cost $0.0928 ($0.00619 per case), median 3.7 s per AI reply.
- claude-opus-5-5: rate 10/10 minus 1 miss(es) ['R10-04'], critical failures 0, cost $0.1941 ($0.01294 per case), median 4.2 s per AI reply.
- Opus miss: R10-04 reply mentioned the archived €50 pickup fee (must_not).
- Rule result: claude-haiku-5-5 (cheapest with 0 critical failures and at most 1 rate miss) is the model for the gated runs.

### visible-4 — 2026-10-20 06:31, development run (not gated)

- Config: eval config v1 · workflows 2f28c39 · claude-haiku-5-5 (effort low, chosen by the model check) + text-embedding-3-small · visible.json 97 cases (c5a9c15f...) · runner exit 0, 619 s.
- Scores: rate 54/55; critical failures 0; critical cases 25/25; code cases 17/17; code metrics all 1.0.
- Result: development run, no verdict.
- Misses: R1-06: reply said "track your order on our website" without the tracking link from A04 (must_include). Newly broken vs visible-3: R1-06 (model change). R5-06 went to handoff (check_failed: a draft named the 250 W motor, not in the cited text); handoff is also OK for R5, so not a miss.
- Changed vs visible-3: model claude-sonnet-5-5 -> claude-haiku-5-5.
- Cost: $0.023 for 97 cases; seconds per AI reply median 2.9, 90th percentile 4.

### visible-5 — 2026-10-20 06:44, development run (not gated)

- Config: eval config v1 · workflows 3bb46b1 · claude-haiku-5-5 (effort low) + text-embedding-3-small · visible.json 97 cases (c5a9c15f...) · runner exit 0, 473 s.
- Scores: rate 55/55; critical failures 0; critical cases 25/25; code cases 17/17; code metrics all 1.0 (log_complete 99/99, handoff_complete 30/30, dont_know_offer 7/7, citation_integrity 44/44, human_mode_silent 1/1, agent_reply_exact 4/4, close_returns 1/1, whatsapp_adapter 7/7, outage_handled 5/5, index_public_only 1/1). No check_failed handoffs.
- Result: development run, no verdict.
- Misses: none. Newly broken vs visible-4: none.
- Changed vs visible-4: prompt rule to include the article's link, e-mail or phone exactly.
- Cost: $0.023 for 97 cases; seconds per AI reply median 2.6, 90th percentile 3.
