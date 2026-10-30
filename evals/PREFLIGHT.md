# PREFLIGHT — before each gated series

The written preflight of the eval-gate build checks (c), checked by hand before each gated series and again
when a series restarts. Not a code guard. "Preflight done <date time>" and any item that needed action go
into the first run's entry in `evals/RESULTS.md`.

Series: hold-out 2 series on the next version (BLUEPRINT v1.10, red-team fixes; eval config v5; owner decisions
2026-10-29), local shared n8n 2.43.7. Order at the slot: push the new workflows, one visible development run (not
gated), then this preflight, the dry run and the 3 gated runs on that one frozen commit. Prepared 2026-10-29 without
n8n (n8n held by Q-117). Items marked "before the series" are filled in at the slot, with the time.

| # | Item | How to check | Status |
|---|---|---|---|
| 1 | The test tools are ours for the whole series | shared notes `n8n-usage.md`: no open line of another build in the window; add "IN USE Q-123 ... GATED", start message to the build sessions listed at its top; Slack `#support-handoff` is this build's own channel | before the series |
| 2 | Every credential works and does not expire before the series ends | see "Credentials" | before the series |
| 3 | Every rate or daily limit on the test path, for 3 runs + 1 rerun | see "Limits" | prepared 2026-10-29 |
| 4 | No KOS rule deploy or tool upgrade during the series | n8n stays 2.43.7 (this build never upgrades or restarts it); ask the planning session whether a KOS deploy or n8n change is planned in the window; no Python or Node upgrade during the series | before the series |
| 5 | One dry case through the full path, runner exit 0 (not a result) | WhatsApp stand-in running (`python tests/mock_whatsapp.py`, 127.0.0.1:8122); `python tests/runner.py run --label dry-4 --only R1-01,H-01` exit 0 (visible cases only; hold-out 2 stays sealed) | before the series |
| 6 | The build in n8n is the frozen build; entry points refuse calls without auth | `python tests/check_n8n_workflows.py` exit 0 (published versions of the 9 Q123 workflows = `workflows/*.json` of the frozen commit, which `workflows/build.py` regenerates unchanged; comparison logic checked offline in `tests/test_runner.py`); one call to `/webhook/q123-message` without the webhook key is refused (403 at P2) | before the series |
| 7 | Hold-out 2 seal | SHA-256 of `holdout2.zip` (folder q123-holdout-2 in the owner's profile) = `evals/holdout2_commitment.json`, checked without opening (match 2026-10-29: 092158fa...; resealed as v2 2026-10-29 with new WhatsApp numbers in HN-W-01..03, owner decision, match 9580c9ae...); open only at gated-h2-1, zip only, into a new empty folder outside the repo; the runner stops if a case ID, WhatsApp number or message ID is in two cases | seal checked 2026-10-29; opening: at the first run |

## Credentials (item 2)

Last proven by use in gated-v3-1..3 (2026-10-20/21) and the web chat dry pass (2026-10-21 02:32).

- Supabase free project `n8n-ai-support-bot`: **likely paused.** Free projects pause after about 7 days
  without use (third-party sources, STATE 2026-10-19); last use 2026-10-21. Fact, 2026-10-29: the project's
  host name does not resolve, while other hosts do (DNS check, no key sent). Inference: the project is
  paused. Action: the owner resumes it in the Supabase dashboard; then the dry run proves search and the
  index check (`index_public_only`).
- n8n credentials `Anthropic n8n-ai-support-bot`, `OpenAI n8n-ai-support-bot`, `Slack n8n-ai-support-bot`:
  proven by the dry run (Claude reply, embedding, Slack handoff with a `ts`). Claude and OpenAI keys do not
  expire unless the owner set a date; Slack bot tokens do not expire unless rotation is on.
- Test-only credentials (`Webhook ...`, `Reply form ...`, `WhatsApp ... (test)`) and `.env` Q123_* values:
  proven by the dry run (H-01 uses the reply form, R1-01 the webhook key).
- n8n API key (`.env` N8N_API_KEY): proven by `tests/check_n8n_workflows.py`; if it has an expiry date, it
  must be after the series end (n8n Settings > n8n API).

## Limits (item 3)

From gated-v3-1..3 (156 cases each, 775-852 s per run, $0.041 per run, 531 customer messages over 3 runs).
A v5 run has 235 cases (107 visible + 59 hold-out seen + 69 hold-out 2), so about 1.5 times:

- time: about 20-22 minutes per run; push + visible run (about 10 minutes) + dry run + 3 runs + 1 rerun about
  2 hours: book a slot of 2 hours;
- Claude (Haiku 5.5) and OpenAI embeddings: about 250 messages per run, far below the account rate limits
  seen so far (no 429 in any earlier run); AI cost about $0.06 per run;
- Slack: about 50-60 handoff posts plus thread appends per run, spaced by the run (no Slack rate error in any
  earlier run);
- Supabase free tier: about 250 searches per run; no limit hit in earlier runs (the 6 search errors of
  gated-seen were before the retry in a0f05b2);
- no e-mail on the test path.
