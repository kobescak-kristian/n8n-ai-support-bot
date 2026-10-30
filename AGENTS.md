# AGENTS.md — n8n-ai-support-bot

Agent-first context router. It points to where repository truth lives.
It is not itself evidence of project state: cite the source it routes
to, never this file.

## Repository purpose

An n8n support bot for a small business: it answers customers only from the business's own help articles, says "I don't know" instead of guessing, hands the conversation to a person in Slack when needed, logs every answer, and has a WhatsApp-ready entry point. Human overview: `README.md`.

## Authority and conflict handling

| Question | Canonical source |
|---|---|
| What the system is and claims | `README.md` |
| Why a design decision was made | `adr/` |
| Build status, decisions, change history | `STATE.md` |
| What the implementation actually does | source, tests and configuration inspected together |

When sources disagree: an adopted ADR outranks the text it amends;
documents state intent, implementation and tests state behaviour, and a
gap between them is a finding to surface, not something to silently
reconcile; `STATE.md` is the status surface; if canonical sources
conflict, stop and ask Kristian.

## Task routing

Starting points, not exhaustive reading lists.

| Task class | Start here |
|---|---|
| Understand or explain the system | `README.md` |
| Current status or decisions | `STATE.md` |
| Scope, design rules, decisions | `README.md` (System), `adr/` |
| Test cases, expected results, behaviour rules | `tests/CASES.md`, `tests/make_cases.py`, `tests/cases/`, `tests/kb/` |
| Grading and eval gate, recorded runs | `tests/grading.py`, `evals/eval_config.yaml`, `evals/RESULTS.md` |
| Workflows (generated) | `workflows/build.py`, `workflows/bot_js.py`; `--push` loads them into n8n through `tools/n8n_api.py` |
| Test runs | `tests/runner.py` (with `tests/mock_whatsapp.py`); knowledge base into Supabase: `tools/index_kb.py`; Supabase setup: `supabase/setup.sql` |
| Documentation / README / ADR work | the artifact itself; `.githooks/validate_artifacts.py` for enforced structure |

## Always-on constraints

- Tier 0 artifacts are README, ADRs, LICENSE, and AGENTS.md.
  STATE.md is separately required by the build-repo STATE rule.
  Do not create SYSTEM_WALKTHROUGH.md, CHANGELOG.md, RUNBOOK.md or
  other trigger-gated artifacts without an instruction citing the
  trigger. ADRs are for genuine material decisions only, with at least
  one required. Version log lives in README.
- Done means the acceptance condition is demonstrated, not that a file
  exists.
- No secrets or machine-local absolute paths in tracked files.
- Never rewrite git history.
- The eval gate is fixed before the build; never change a case, expected
  result, KB article, grading rule or threshold to make a run pass (new dated version only).
- The hold-out cases are written by a separate session. A building
  session never opens the hold-out folder before the first gated run.
- Made-up data only (company, people, orders); no real business accounts.
- This file is an instruction surface, not a security boundary.

## Verification

- Tier 0 structure: `python .githooks/validate_artifacts.py .`
- Test cases and self-checks: `python tests/make_cases.py`
- Grader catches what it should: `python tests/test_grading.py`
- Runner grading and scoring offline: `python tests/test_runner.py`
- Workflow files regenerate: `python workflows/build.py`; in-n8n checks offline: `python tests/test_bot_js.py` (node)
