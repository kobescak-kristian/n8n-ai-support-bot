# STATE — n8n-ai-support-bot

n8n AI support bot with human handoff, WhatsApp-ready (answers only from a made-up company's help articles, "I don't know" instead of guessing, handoff to a person in Slack, every answer logged); Upwork portfolio item 6 (Q-123) to support winning a first client.
**Classification:** PROJECT · T0
**Plan:** Blueprint locked by the owner 2026-10-19 (planning session; written in the shared side-session notes as item6-support-bot-plan.md, committed here as BLUEPRINT.md with the eval gate). Phases: P0 scaffold -> P1 eval gate (KB, case rules, visible cases, config; no workflow code) -> P1b hold-out by a separate session, sealed by SHA-256 -> P2 owner creates accounts -> P3 core + web chat (waits for the owner's "n8n is free") -> P4 handoff, WhatsApp adapter, outages, logging -> P5 model check, 3 gated runs -> P6 README, cover image, Loom. Eval level: Decided Critical, owner, 2026-10-19. `Safeguard removed: human approval before each customer reply, owner, 2026-10-19` (replaced by code checks; any failed check = handoff).
**Stack (owner decisions 2026-10-19):** local n8n 2.43.7 (shared with other builds: names prefixed Q123, tag q123, data tables q123_*, webhooks /webhook/q123-*; never restart or reconfigure n8n) · Claude via a new Anthropic workspace `n8n-ai-support-bot` (owner creates) · OpenAI embeddings text-embedding-3-small, new OpenAI project (owner creates) · Supabase free project (owner creates; pgvector table and match function from a committed SQL file with explicit grants) · Slack demo workspace, new app "Support Bot", channel #support-handoff · WhatsApp entry point tested on made-up payloads only; no live number (no Meta business account). Made-up company "Harbour E-Bikes"; no real business accounts, no real customer data (F-112).
**Status:** scaffold only.
**Open decisions:** none
**Decisions:** none yet

## Change Log
*(New entries on top. Phase closes require evidence: exit codes,
commit hashes, eval numbers.)*

- **2026-10-19** — Scaffold (new-project, standard). Plan approved by the owner 2026-10-19 (planning session).
