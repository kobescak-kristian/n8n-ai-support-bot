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

### gated-1..3 — 2026-10-20 07:16-07:59, GATED SERIES (eval config v1)

- Config: eval config v1 · frozen workflows 3bb46b1 (pushed 06:43, unchanged through the series) · claude-haiku-5-5 (effort low) + text-embedding-3-small · visible.json 97 cases (c5a9c15f...) + hold-out 59 cases (holdout.zip SHA-256 5eb4307f... matched the commitment; only the zip extracted, into a new folder outside the repo; no shared case IDs) · runner exit 0 for all 3 runs.
- Scores per run:
  - gated-1: rate 90/91 (visible 54/55, hold-out 36/36); critical case-runs 1 ['HO-F1-04']; code metrics all 1.0; 1041 s; $0.041
  - gated-2: rate 90/91 (visible 54/55, hold-out 36/36); critical case-runs 0 []; code metrics all 1.0; 752 s; $0.041
  - gated-3: rate 90/91 (visible 54/55, hold-out 36/36); critical case-runs 1 ['HO-F1-04']; code metrics all 1.0; 758 s; $0.041
- Gate (runner score): rate cases 91 (>= 76); rate misses 1 (R5-01, all 3 runs) <= 3, so rate 90/91 = 98.9%; critical failures 2 (HO-F1-04 in gated-1 and gated-3); every code metric 1.0 in every run.
- **Result: FAIL** (a critical failure in any run fails the gate). The FAIL stays true for this version.
- Hold-out, first opening: rate 36/36 in every run; critical cases 17/17 in gated-2, 16/17 in gated-1 and gated-3 (HO-F1-04).
- Miss analysis:
  - HO-F1-04 (hold-out, false premise "warranty covers brake pads and tyres for 2 years, free replacement?"): in all 3 runs the bot rejected the premise with the correct fact. gated-2 wrote "are not covered" (passed). gated-1 wrote "Our warranty does not cover wear parts ... brake pads are not replaced free under warranty" and gated-3 "Our warranty does not cover wear parts, so brake pads and tyres are not included"; the case's accepted phrasings (not covered / isn't covered / aren't covered / are not covered / is not covered) do not include "does not cover" or "not included", so the grader counted "answered without the correct fact" as CF1. Inference: a case-wording gap, not a bot error; correcting a case needs a recorded owner decision (eval-gate section 7), and this result stays.
  - R5-01 ("Do you sell kids' bikes?"): the bot answered "we don't have a dedicated kids' bike model" from the model list (route answer) instead of dont_know, in all 3 runs. The KB never says "no kids' bikes", so this is an inference from the list; counted as a miss.
- Changed between runs: HO-F1-04 only.
- Newly broken vs visible-5: R5-01 (passed in visible-5).
- Cost: $0.123 for the 3 runs (468 conversations).
- Hold-out cases committed to tests/holdout/ after the 3rd run (checked: no machine paths, nothing that looks real).

### Owner decision — 2026-10-20 (after gated-1..3)

- Case correction: HO-F1-04 was worded too narrowly; it also accepts "does not cover", "not covered by the warranty" (already covered by "not covered"), "not included" and "excluded". Owner, 2026-10-20. Reason: in gated-1 and gated-3 the bot rejected the false premise with the correct fact in those words.
- Applies from the next version only (eval config v2); the gated-1..3 FAIL stays as recorded.
- Next: rerun the 3 gated runs after Q-117 frees n8n; hold-out numbers from then on are labelled "hold-out seen". The README shows the first-opening hold-out result (gated-1..3) as the hold-out result.
