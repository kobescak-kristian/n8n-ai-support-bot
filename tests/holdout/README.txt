Q-123 hold-out cases (n8n AI support bot, Harbour E-Bikes). Written 2026-10-19 by a separate session that never builds the bot.
cases.json uses the same format as tests/cases/visible.json (tests/CASES.md section 6). Grade R and F cases with
tests/grading.py grade_reply, passing the conversation_canaries of ALL cases (visible + hold-out) as extra_canaries.
Code cases (S, W, H) use the same keys as the visible code cases; HO-H-02 adds expect.reason (the log row reason).
Open only at the first gated run, after checking the SHA-256 in evals/holdout_commitment.json. Made-up data only.
