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

### check-6 — 2026-10-20 20:19, development check (not gated)

- Config: eval config v2 · workflows b9dcbda (prompt rule after R5-01) · claude-haiku-5-5 · 24 visible cases (R5, R1, R10, F1) · runner exit 0.
- Scores: rate 19/19 (R5-01 passes); critical cases 5/5; critical failures 0; code metrics 1.0 (log_complete 28/28, dont_know_offer 7/7, citation_integrity 21/21, index_public_only 1/1).
- Result: development check, no verdict. Changed vs gated-1..3: prompt rule only. Cost: $0.0082.

### gated-seen-1..3 — 2026-10-20 20:26-21:08, GATED SERIES, hold-out seen (eval config v2)

- Config: eval config v2 (HO-F1-04 corrected by owner decision) · frozen workflows b9dcbda (deployed 20:19, unchanged through the series) · claude-haiku-5-5 (effort low) + text-embedding-3-small · visible.json 97 cases + tests/holdout/cases.json 59 cases (hold-out seen: opened in gated-1..3) · runner exit 0 for all 3 runs.
- Scores per run:
  - gated-seen-1: rate 90/91 (hold-out seen 35/36); critical failures 0; critical cases 39/42; code cases 22/23; code metrics all 1.0; 876 s; $0.040
  - gated-seen-2: rate 90/91 (hold-out seen 35/36); critical failures 0; critical cases 41/42; code cases 23/23; code metrics all 1.0; 807 s; $0.041
  - gated-seen-3: rate 89/91 (hold-out seen 35/36); critical failures 0; critical cases 42/42; code cases 23/23; code metrics all 1.0; 778 s; $0.041
- Gate (runner score, rules as frozen): rate cases 91 (>= 76); rate misses 3 (R3-01, HO-R6-03, HO-R10-03) <= 3, so 88/91 = 96.7%; critical failures 0 in every run; every code metric 1.0 in every run.
- **Result: PASS (hold-out seen)**, at the limit of allowed misses. Recorded as the frozen rules give it; owner decision 2026-10-20: record PASS with the caveats below and fix them as the next version.
- Caveats (facts from the logs):
  - 6 unplanned Supabase search errors in gated-seen-1 (4) and gated-seen-2 (2), between 20:30 and 20:50; none in gated-seen-3. Each time the customer got FALLBACK_TEXT and an alert was posted; nothing wrong was said. Lost correct answers: HO-R6-03 (rate, counted as a miss), F1-02, F1-05, F2-02, F4-01 (critical cases; graded only by the critical checks, so they pass), H-05 (code case; its handoff did not happen). The workflow had no retry on the Supabase search, and the error code was not logged.
  - Scoring gap: code case H-05 failed in gated-seen-1, but no code metric fell below 1.0, because no metric covers "every code case passes". The PASS is under the rules as frozen.
  - The other two misses are the safety net blocking correct replies: HO-R10-03 (Italian "under 18" for "aged 16 or 17": 18 not in the article) and R3-01 ("€0" for free delivery: 0 not in the article); both went to a person (handoff), not a wrong answer.
- Changed between runs: F1-02, F1-05, F2-02, F4-01, H-05, HO-R6-03 (Supabase errors), HO-R10-03, R3-01 (safety-net blocks).
- Newly broken vs gated-1..3: R3-01, HO-R6-03, HO-R10-03 (each passed in gated-1..3).
- Cost: $0.122 for the 3 runs.
- Next version (owner decision): one retry on the Supabase search and the embedding call, error codes in the log; gate v3 adds a code metric "every code case passes"; failure-register entries for the scoring gap and the missing retry.

### check-7 — 2026-10-20 22:35, development check of the next version (not gated)

- Config: eval config v3 · workflows a0f05b2 (one retry on Supabase search and embeddings, error codes logged) · claude-haiku-5-5 · 8 visible cases (S-01..S-04, R1-01, R7-01, W-01, H-01) · runner exit 0.
- Scores: rate 2/2; code cases 6/6 (code_cases_pass 6/6); outage_handled 4/4; critical failures 0; all code metrics 1.0.
- The 4 simulated outages now log their error ("The service refused the connection") and take 2.4-5.7 s with the retry.
- Result: development check, no verdict. Claims about this version need its own gated series.

### gated-seen-1..3 secondary metrics (reported, not gated) — computed 2026-10-20 from the runs' raw reports

- Customer messages logged: 531 over the 3 runs; replies that called Claude: 430.
- Seconds from message received to reply, replies that called Claude: median 2.6, 90th percentile 3.5.
- AI cost (Claude + embeddings, from logged tokens): $0.122 for the 3 runs, $0.00023 per customer message.
- Handoffs: 142 of 531 messages (26.7%), most by design (person requests, complaints, safety, order status).

### gated-v3-1..3 — 2026-10-20 23:20 to 2026-10-21 00:01, GATED SERIES, hold-out seen (eval config v3)

- Config: eval config v3 (adds code_cases_pass) · frozen workflows a0f05b2 (retry on the Supabase search and the embedding call, error codes logged; deployed 2026-10-20 22:35, unchanged through the series) · claude-haiku-5-5 (effort low) + text-embedding-3-small · visible.json 97 cases + tests/holdout/cases.json 59 cases (hold-out seen) · runner exit 0 for all 3 runs.
- Scores per run:
  - gated-v3-1: rate 89/91 (hold-out seen 34/36); critical failures 0; critical cases 42/42; code_cases_pass 23/23; all code metrics 1.0; 852 s; $0.041
  - gated-v3-2: rate 91/91 (hold-out seen 36/36); critical failures 0; critical cases 42/42; code_cases_pass 23/23; all code metrics 1.0; 793 s; $0.041
  - gated-v3-3: rate 91/91 (hold-out seen 36/36); critical failures 0; critical cases 42/42; code_cases_pass 23/23; all code metrics 1.0; 775 s; $0.041
- Gate (runner score): rate cases 91 (>= 76); rate misses 2 (HO-R5-02, HO-R10-03) <= 3, so 89/91 = 97.8%; critical failures 0 in every run; every code metric 1.0 in every run, including code_cases_pass 23/23.
- **Result: PASS (hold-out seen).**
- Unplanned outages: 0 in the 3 runs (531 customer messages).
- Miss analysis:
  - HO-R5-02 (gated-v3-1 only): a question about the Harbour Trail's motor brand and suspension fork; the bot gave the one fact the articles hold (250 W motor) and said it could not confirm the rest, as route answer instead of dont_know.
  - HO-R10-03 (gated-v3-1 only): the reply check blocked a correct Italian reply ("under 18" for "aged 16 or 17"; 18 is not in the article), so the conversation went to a person; the follow-up message then had no bot reply. Same cause as in gated-seen-1 and gated-seen-3.
  - Other reply-check blocks that went to a person where that is also allowed (not misses): HO-R5-03, HO-F1-02 (gated-v3-2), R5-06 (gated-v3-3).
- Changed between runs: HO-R5-02, HO-R10-03.
- Newly broken vs gated-seen-1..3: HO-R5-02. Fixed vs gated-seen-1..3: R3-01, HO-R6-03.
- Secondary (reported, not gated): median 2.6 s per reply that called Claude, 90th percentile 3.3; AI cost $0.123 for the 3 runs, $0.00023 per customer message; 531 customer messages.

### visible-6 — 2026-10-29 20:09-20:17, development run (not gated)

- Config: eval config v5 · workflows v1.10 (commit 6457852, loaded into n8n 2026-10-29 about 19:05; `tests/check_n8n_workflows.py` exit 0: n8n runs the committed workflows) · claude-haiku-5-5 + text-embedding-3-small · visible.json 107 cases (no hold-out) · runner exit 0.
- Scores: rate 57/57; critical case-runs 0; every code metric 1.0 (log_complete 114/114, handoff_complete 36/36, dont_know_offer 8/8, citation_integrity 51/51, human_mode_silent 1/1, agent_reply_exact 4/4, close_returns 1/1, whatsapp_adapter 10/10, outage_handled 6/6, index_public_only 1/1, code_cases_pass 21/21); 503 s.
- Misses: none. The 10 cases added in v5 all pass.
- Reply-check blocks that went to a person where that is also allowed (not misses): F1-06 (the customer wrote "sixty" and "forty" as words; the bot's correct reply said 60 and 40 in digits, which the number check cannot match to words).
- Secondary (reported, not gated): 125 log rows; median 2.5 s per reply that called Claude; AI cost $0.027.
- Next: the second build red team (19 findings, run on the code before this run) led to v1.11; the gated series waits for v1.11, its checks and the third red team.

### visible-7 — 2026-10-30 21:28-21:37, development run (not gated)

- Config: eval config v7 · workflows v1.12 (commit 63f4b97, loaded into n8n 2026-10-30 about 20:20; `tests/check_n8n_workflows.py` exit 0: n8n runs the committed workflows; the run record shows the same workflow hash 5523ceed... and a clean working tree) · claude-haiku-5-5 + text-embedding-3-small · visible.json 107 cases (no hold-out) · runner exit 0.
- Scores: rate 57/57; critical case-runs 0; every code metric 1.0 (log_complete 114/114, handoff_complete 36/36, dont_know_offer 8/8, citation_integrity 51/51, human_mode_silent 1/1, agent_reply_exact 4/4, close_returns 1/1, whatsapp_adapter 10/10, outage_handled 6/6, index_public_only 1/1, code_cases_pass 21/21); 508 s.
- Misses: none.
- Reply-check blocks that went to a person where that is also allowed (not misses): F1-06, same cause as in visible-6 (the customer wrote "sixty" as a word; the bot's correct reply said 60 in digits).
- Changed vs visible-6: workflows v1.10 -> v1.12 and eval config v5 -> v7 (fixes from the second, third and last build red team and the short red team on v1.12); every case has the same result as in visible-6.
- Secondary (reported, not gated): 125 log rows; median 2.4 s per reply that called Claude (95 replies); AI cost $0.027.
- Next: the preflight (evals/PREFLIGHT.md), a 2-case dry run and the gated series on hold-out 2.
