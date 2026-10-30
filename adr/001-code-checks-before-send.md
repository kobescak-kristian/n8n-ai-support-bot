# ADR-001: Code checks every reply before it is sent; a failed check hands off to a person

**Status:** Accepted (2026-10-21)
Date: 2026-10-21
Author: Kristian Kobescak (decision, 2026-10-19); recorded by Claude Code

## Context

The bot replies to customers with no person reading each reply first. At
eval level Critical the default safeguard is "a person approves each send",
which would remove the point of a support bot (customers wait for a person
every time). That safeguard was removed on 2026-10-19 on the condition
that automatic checks stop risky replies (BLUEPRINT.md section 5:
`Safeguard removed: human approval before each customer reply, Kristian,
2026-10-19`; decisions 2 and 3 in section 7). The critical failures the
safeguard must stop are a made-up fact, a false promise or discount code,
and a leak (eval config CF1 to CF3).

## Decision

Before any AI-written reply is sent, plain code (no AI) checks it, and any
failed check means nothing from the AI is sent and the conversation is
handed to a person in Slack with reason `check_failed`.

The checks (tests/CASES.md rule 8): every number, e-mail address and link in
the reply appears in the articles the reply cites or in the customer's own
messages; no code-like string (such as `SAVE20`) that is not in them; no
canary text; every cited article was really retrieved; the reply is not
empty and at most 1,000 characters.

## Alternatives rejected

- **A person approves each reply** (the default Critical safeguard): turns
  the bot into a draft writer; every customer waits for a person. Rejected
  on 2026-10-19.
- **A second AI call judges the reply before sending:** slower and more
  expensive per message, and the judge can itself be wrong in the same ways
  as the writer; its errors would also be hard to explain to a client.
  Rejected in BLUEPRINT.md decision 2.
- **No check, rely on the prompt:** the gated tests include made-up-fact,
  discount and injection bait (F1 to F3); a prompt alone gives no guarantee
  that a number in a reply exists in the articles.

## Consequences

- The checks block some correct replies: a paraphrase that introduces a new
  number ("under 18" for "aged 16 or 17", "€0" for "free"), or a computed
  total ("€150 + €5 per day = €185"). The customer then gets a person, not
  a wrong answer. Recorded in evals/RESULTS.md (gated-seen-1..3,
  gated-v3-1..3: HO-R10-03, R3-01 and others).
- The checks cannot catch a wrong fact that reuses a number from the cited
  article in the wrong place, or a wrong claim with no number in it. The
  prompt and the critical test cases cover those; the gate measures them.
- The rule "give the parts, not computed totals" is part of the prompt,
  because a computed total is always blocked.

## Verification (code-verified 2026-10-21)

- `python tests/test_bot_js.py` → "all checks hold": replyChecks passes good
  replies and blocks a computed total, a number from another article, a
  code-like string, an unknown link, canary text and a too-long reply (10
  samples), using the generated Core workflow code.
- workflows/bot_js.py `FINALIZE`: any failed check sets route `handoff`,
  reason `check_failed`, keeps the blocked draft in the log, sends no AI text.
- Gated series gated-v3-1..3 on workflows a0f05b2 (evals/RESULTS.md, commit
  7abdebc): 0 critical failures in 3 runs of 156 cases.

## Review

Reopen if a gated series records a critical failure that the checks should
have stopped, or if blocks of correct replies exceed 3 misses in a gated
series; otherwise review when the bot is adapted for a real client's
knowledge base.
