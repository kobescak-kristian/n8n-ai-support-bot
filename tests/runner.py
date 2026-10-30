"""Test runner for the n8n AI support bot (Q-123).

Sends every case through the bot's webhooks, plays scripted agent steps through
the reply form's submit endpoint, reads the report, grades each case with
tests/grading.py and writes one results file per run. `score` combines 3 runs
into the gate verdict of evals/eval_config.yaml.

  python tests/runner.py run --label dev-1 [--only R1-01,W-02] [--data <folder> [--data <folder>]]
  python tests/runner.py score --labels gated-1 gated-2 gated-3

Webhook contract the workflows implement (all on http://localhost:5678/webhook/):
  q123-message       POST {conversation_id, channel, text, simulate, run_label}
                     -> {route, reply, cited, reason, log_id}        (test entry; same core as web chat)
  q123-whatsapp      POST Meta webhook body, header X-Hub-Signature-256 (WhatsApp adapter)
  q123-agent-submit  POST form {conversation_id, action: reply|close, text}  (reply form submit)
  q123-report        POST {run_label} -> {log, handoffs, outbox, index}
  q123-reset         POST {run_label} -> clears conversations, log, handoffs, outbox for the label
Secrets come from the ignored local .env (Q123_WEBHOOK_KEY, Q123_FORM_USER, Q123_FORM_PASSWORD,
Q123_WA_TEST_SECRET). Results: tests/results/<label>.json (summary, committed) and
tests/results/raw/<label>.json (full replies, ignored).
"""

import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import grading  # noqa: E402

BASE = "http://localhost:5678/webhook/"
WA_MOCK = "http://127.0.0.1:8122"
CODE_METRICS = ["log_complete", "handoff_complete", "dont_know_offer", "citation_integrity", "human_mode_silent",
                "agent_reply_exact", "close_returns", "whatsapp_adapter", "outage_handled", "index_public_only",
                "code_cases_pass"]
LOG_FIELDS = ["ts", "channel", "conversation_id", "message", "route", "reason", "reply", "retrieved", "cited",
              "checks", "model", "tokens_in", "tokens_out", "cost", "seconds", "simulated"]


# ---------------- setup ----------------

def load_env():
    env = {}
    p = ROOT.parent / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    env.update({k: v for k, v in os.environ.items() if k.startswith("Q123_")})
    return env


def load_cases(data):
    """Visible cases plus each extra folder's cases.json (v4: tests/holdout, then the hold-out 2 folder).
    Stops on a case ID twice (inside a file or across files) and, v5 (red team 26), on a WhatsApp number or
    WhatsApp message ID used by two cases: every case of a run shares the bot's state for that number."""
    sets = [json.loads((ROOT / "cases" / "visible.json").read_text(encoding="utf-8"))["cases"]]
    sets += [json.loads((Path(d) / "cases.json").read_text(encoding="utf-8"))["cases"] for d in data or []]
    cases = []
    for extra in sets:
        ids = [c["id"] for c in extra]
        dup = sorted({i for i in ids if ids.count(i) > 1})
        if dup:
            sys.exit(f"stop: case IDs twice in one set: {dup}")
        clash = sorted({c["id"] for c in cases} & set(ids))
        if clash:
            sys.exit(f"stop: case IDs in both sets: {clash}")
        cases += extra
    for what, key in (("WhatsApp numbers", _wa_numbers), ("WhatsApp message IDs", _wa_message_ids)):
        owner, shared = {}, set()
        for c in cases:
            for x in key(c):
                if owner.setdefault(x, c["id"]) != c["id"]:
                    shared.add(f"{x} ({owner[x]}, {c['id']})")
        if shared:
            sys.exit(f"stop: {what} used by two cases: {sorted(shared)}")
    return cases


def _wa_events(c):
    for p in c.get("payloads", []):
        for e in p.get("entry", []):
            for ch in e.get("changes", []):
                v = ch.get("value", {})
                yield from (("m", m) for m in v.get("messages", []))
                yield from (("s", st) for st in v.get("statuses", []))


def _wa_numbers(c):
    out = {m.get("from") if k == "m" else m.get("recipient_id") for k, m in _wa_events(c)}
    if c.get("kind") == "H" and c.get("channel") == "whatsapp":
        out.add(c.get("wa_id"))
    return out - {None}


def _wa_message_ids(c):
    return {m.get("id") for k, m in _wa_events(c) if k == "m"} - {None}


def http(method, url, body=None, form=None, headers=None, timeout=180):
    data, h = None, dict(headers or {})
    if body is not None:
        data, h["Content-Type"] = json.dumps(body).encode("utf-8"), "application/json"
    elif form is not None:
        data, h["Content-Type"] = urllib.parse.urlencode(form).encode("utf-8"), "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8")
            return r.status, (json.loads(raw) if raw.strip().startswith(("{", "[")) else raw)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


class Bot:
    def __init__(self, env, label):
        self.env, self.label = env, label
        self.key = {"X-Webhook-Key": env.get("Q123_WEBHOOK_KEY", "")}
        cred = f"{env.get('Q123_FORM_USER', '')}:{env.get('Q123_FORM_PASSWORD', '')}".encode()
        self.form_auth = {"Authorization": "Basic " + base64.b64encode(cred).decode()}

    def message(self, conv, channel, text, simulate=None):
        body = {"conversation_id": conv, "channel": channel, "text": text, "simulate": simulate, "run_label": self.label}
        s, r = http("POST", BASE + "q123-message", body=body, headers=self.key)
        return r if s == 200 and isinstance(r, dict) else {"route": None, "reply": None, "error": f"HTTP {s}: {r}"}

    def whatsapp(self, payload, signature="good"):
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        secret = self.env.get("Q123_WA_TEST_SECRET", "") if signature == "good" else "not-the-app-secret"
        sig = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        req = urllib.request.Request(BASE + "q123-whatsapp", data=raw, method="POST",
                                     headers={"Content-Type": "application/json", "X-Hub-Signature-256": "sha256=" + sig})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code

    def agent(self, conv, action, text=""):
        form = {"conversation_id": conv, "action": action, "text": text}
        return http("POST", BASE + "q123-agent-submit", form=form, headers=self.form_auth)[0]

    def report(self):
        s, r = http("POST", BASE + "q123-report", body={"run_label": self.label}, headers=self.key)
        if s != 200 or not isinstance(r, dict):
            raise RuntimeError(f"report failed: HTTP {s}")
        return r

    def reset(self):
        return http("POST", BASE + "q123-reset", body={"run_label": self.label}, headers=self.key)[0]


def wa_sends():
    s, r = http("GET", WA_MOCK + "/_sends")
    return r if s == 200 else []


def wait_sends(before, expect, quiet=6.0, limit=60.0):
    """WhatsApp replies are sent after the entry has answered Meta, so wait: until at least `expect` new sends
    arrived and nothing new came for `quiet` seconds (or `limit` seconds passed)."""
    t0, last_n, last_change = time.time(), -1, time.time()
    while time.time() - t0 < limit:
        n = len(wa_sends()) - before
        if n != last_n:
            last_n, last_change = n, time.time()
        if n >= expect and time.time() - last_change >= quiet:
            break
        time.sleep(0.5)
    return wa_sends()[before:]


def wa_reset():
    http("POST", WA_MOCK + "/_reset", body={})


# ---------------- playing cases ----------------

def play(bot, c):
    """Send one case. Returns the raw record; grading happens after the report is read."""
    rec = {"id": c["id"], "kind": c["kind"], "group": c["group"], "steps": []}
    base = f"{bot.label}:{c['id']}"
    if c["group"] in ("rate", "critical"):
        for i, prior in enumerate(c.get("prior_conversations", [])):
            for t in prior:
                rec["steps"].append({"conv": f"{base}:p{i}", "sent": t,
                                     "resp": bot.message(f"{base}:p{i}", c["channel"], t)})
        for t in c["turns"]:
            rec["steps"].append({"conv": f"{base}:m", "sent": t, "resp": bot.message(f"{base}:m", c["channel"], t)})
    elif c["kind"] == "S":
        for t in c["turns"]:
            rec["steps"].append({"conv": f"{base}:m", "sent": t,
                                 "resp": bot.message(f"{base}:m", c["channel"], t, simulate=c["simulate"])})
    elif c["kind"] == "W":
        before = len(wa_sends())
        def _wait_one(n0=None, limit=20.0):
            n0 = len(wa_sends()) if n0 is None else n0
            t0 = time.time()
            while time.time() - t0 < limit and len(wa_sends()) <= n0:
                time.sleep(0.5)
        for p in c["payloads"]:
            n_before = len(wa_sends())
            rec["steps"].append({"payload_id": _wa_ids(p), "http": bot.whatsapp(p, c.get("signature", "good"))})
            _wait_one(n_before)  # let this payload finish (memory for the next one) or time out
        rec["wa_sends"] = wait_sends(before, len(c["expected"]["sends"]), quiet=8 if not c["expected"]["sends"] else 4)
    elif c["kind"] == "H":
        before = len(wa_sends())
        for st in c["script"]:
            conv = f"{base}:{st.get('conversation', 'm')}"
            if c["channel"] == "whatsapp":
                conv = "wa:" + c["wa_id"]
            if "customer" in st:
                if c["channel"] == "whatsapp":
                    n0 = len(wa_sends())
                    rec["steps"].append({"conv": conv, "sent": st["customer"],
                                         "http": bot.whatsapp(_wa_text(c["wa_id"], st["customer"], len(rec["steps"])))})
                    wait_sends(n0, 1, quiet=2)  # the bot's reply (or handoff text) is sent once the core is done
                else:
                    rec["steps"].append({"conv": conv, "sent": st["customer"], "resp": bot.message(conv, "webchat", st["customer"])})
            elif "agent_reply" in st:
                rec["steps"].append({"conv": conv, "agent_reply": st["agent_reply"], "http": bot.agent(conv, "reply", st["agent_reply"])})
            elif st.get("agent_close"):
                rec["steps"].append({"conv": conv, "agent_close": True, "http": bot.agent(conv, "close")})
        rec["wa_sends"] = wait_sends(before, 0, quiet=4)
    return rec


def _wa_ids(p):
    v = p["entry"][0]["changes"][0]["value"]
    return [m["id"] for m in v.get("messages", [])] or [s["id"] for s in v.get("statuses", [])]


def _wa_text(wa_id, text, n):
    return {"object": "whatsapp_business_account", "entry": [{"id": "WABA-TEST-0001", "changes": [{"value": {
        "messaging_product": "whatsapp", "metadata": {"display_phone_number": "0100 555 0100", "phone_number_id": "PNID-TEST-0001"},
        "contacts": [{"profile": {"name": "Test Customer"}, "wa_id": wa_id}],
        "messages": [{"from": wa_id, "id": f"wamid.H.{wa_id}.{n}", "timestamp": "1792400000", "type": "text",
                      "text": {"body": text}}]}, "field": "messages"}]}]}


# ---------------- grading one run ----------------

def grade_run(cases, records, report, kb):
    log = report.get("log", [])
    handoffs = {h["conversation_id"]: h for h in report.get("handoffs", [])}
    all_handoffs = {}
    for h in report.get("handoffs", []):
        all_handoffs.setdefault(h["conversation_id"], []).append(h)
    extra = [p for c in cases for p in c.get("conversation_canaries", [])]
    by_id = {c["id"]: c for c in cases}
    out, crit_total = {}, 0
    metric = {m: [0, 0] for m in CODE_METRICS}  # [ok, total]

    def tally(name, ok):
        metric[name][1] += 1
        metric[name][0] += int(bool(ok))

    for rec in records:
        c = by_id[rec["id"]]
        res = {"passed": True, "misses": [], "critical": []}
        convs = {}
        for st in rec["steps"]:
            if "sent" in st:
                convs.setdefault(st["conv"], []).append(st["sent"])
            r = st.get("resp") or {}
            if r.get("reply"):
                for code, d in grading.critical_checks(r["reply"], convs[st["conv"]], kb, extra):
                    res["critical"].append((code, d))
            if r.get("route") == "dont_know":
                tally("dont_know_offer", grading.OFFER_LINE in (r.get("reply") or ""))
            if r.get("route") == "answer":
                row = next((x for x in log if x.get("log_id") == r.get("log_id")), {})
                retrieved = {x.get("id") for x in row.get("retrieved") or []}
                tally("citation_integrity", set(r.get("cited") or []) <= retrieved)
            if r.get("route") == "handoff":
                h = handoffs.get(st["conv"]) or {}
                text = h.get("slack_text") or ""
                tally("handoff_complete", h.get("slack_ok") and h.get("reason") and h.get("form_link")
                      and all(t in text for t in convs[st["conv"]]))
        if c["group"] in ("rate", "critical"):
            last = rec["steps"][-1]
            result = dict(last.get("resp") or {})
            result["handoff_record"] = handoffs.get(last["conv"])
            g = grading.grade_reply(c, result, convs[last["conv"]], kb, extra)
            res["misses"] += g["misses"]
            res["critical"] += [x for x in g["critical"] if x not in res["critical"]]
        elif c["kind"] == "S":
            r = rec["steps"][-1].get("resp") or {}
            row = next((x for x in log if x.get("conversation_id") == rec["steps"][-1]["conv"]), {})
            parts = c["expected"].get("reply_exact", "FALLBACK_TEXT")
            want = " ".join(getattr(grading, k) for k in ([parts] if isinstance(parts, str) else parts))
            ok = (r.get("reply") == want and row.get("simulated") is True
                  and row.get("alert_status") == c["expected"]["alert"])
            tally("outage_handled", ok)
            if not ok:
                res["misses"].append(f"outage: reply/alert/simulated wrong ({row.get('alert_status')})")
        if c["kind"] in ("W", "H"):  # v5 (red team 22): CF checks also on replies sent through the WhatsApp adapter
            agent_texts = {st["agent_reply"] for st in c.get("script", []) if "agent_reply" in st}
            cust = [m.get("text", {}).get("body", "") for k, m in _wa_events(c) if k == "m"] + \
                   [st["sent"] for st in rec["steps"] if "sent" in st]
            for snd in rec.get("wa_sends", []):
                text = (snd["body"].get("text") or {}).get("body", "")
                if text and text not in agent_texts:
                    for code, d in grading.critical_checks(text, cust, kb, extra):
                        if (code, d) not in res["critical"]:
                            res["critical"].append((code, d))
        if c["kind"] == "W":
            ok, why = _check_wa(c, rec, log)
            tally("whatsapp_adapter", ok)
            if not ok:
                res["misses"].append("whatsapp: " + why)
        elif c["kind"] == "H":
            for why in _check_h(c, rec, report, handoffs, tally, all_handoffs):
                res["misses"].append("handoff flow: " + why)
        if res["critical"]:
            res["misses"].append("critical: " + "; ".join(f"{a} {b}" for a, b in res["critical"]))
        res["passed"] = not res["misses"]
        if c["group"] == "code":  # gate v3: every code case passes (gap found in gated-seen-1, H-05)
            tally("code_cases_pass", res["passed"])
        crit_total += bool(res["critical"])
        out[c["id"]] = res

    sent = [st for rec in records for st in rec["steps"] if "sent" in st]
    rows_by_msg = {}
    for row in log:
        rows_by_msg.setdefault((row.get("conversation_id"), row.get("message")), []).append(row)
    times_sent = {}
    for st in sent:
        times_sent[(st["conv"], st["sent"])] = times_sent.get((st["conv"], st["sent"]), 0) + 1
    for st in sent:
        rows = rows_by_msg.get((st["conv"], st["sent"]), [])
        tally("log_complete", len(rows) == times_sent[(st["conv"], st["sent"])] and all(f in r for r in rows for f in LOG_FIELDS))
    idx = report.get("index", {})
    public = {k for k, a in kb.items() if a["meta"]["visibility"] == "public"}
    tally("index_public_only", set(idx.get("public_article_ids", [])) == public and idx.get("internal_chunks") == 0)
    return out, crit_total, {m: (ok / tot if tot else None, ok, tot) for m, (ok, tot) in metric.items()}


def _check_wa(c, rec, log):
    exp, sends = c["expected"], rec["wa_sends"]
    if len(sends) != len(exp["sends"]):
        return False, f"{len(sends)} sends, expected {len(exp['sends'])}"
    for s, e in zip(sends, exp["sends"]):
        b = s["body"]
        text = (b.get("text") or {}).get("body", "")
        if b.get("to") != e["to"] or not text or len(text) > e.get("max_chars", 4096):
            return False, f"send to {b.get('to')} / text length {len(text)}"
        if e.get("text_exact") and text != getattr(grading, e["text_exact"]):
            return False, "media text not exact"
        for g in e.get("must_include", []):
            if not any(grading.contains(text, alt) for alt in g):
                return False, f"missing one of {g}"
    wa_rows = [r for r in log if r.get("channel") == "whatsapp" and r.get("message_id") in
               {i for st in rec["steps"] for i in st.get("payload_id", [])}]
    if "http_status" in exp and any(st.get("http") not in exp["http_status"] for st in rec["steps"]):
        return False, "bad signature not refused with 401/403"
    if "ai_calls" in exp and sum(1 for r in wa_rows if r.get("ai_called")) != exp["ai_calls"]:
        return False, "AI-call count"
    if "message_log_rows" in exp and len(wa_rows) != exp["message_log_rows"]:
        return False, "log rows for status updates"
    for e in exp["sends"]:
        if "ai_called" in e and not any(r.get("ai_called") == e["ai_called"] for r in wa_rows):
            return False, "ai_called flag"
    return True, ""


def _check_h(c, rec, report, handoffs, tally, all_handoffs=None):
    whys, outbox = [], report.get("outbox", [])
    steps = [s for s in rec["steps"]]
    for st, spec in zip(steps, c["script"]):
        e = spec["expect"]
        r = st.get("resp") or {}
        if "customer" in spec and c["channel"] == "webchat":
            if e.get("route") and r.get("route") != e["route"]:
                whys.append(f"route {r.get('route')} for '{spec['customer']}', expected {e['route']}")
            if "reply_exact" in e:
                want = getattr(grading, e["reply_exact"]) if e["reply_exact"] else None
                if (r.get("reply") or None) != want:
                    whys.append("reply text not as expected")
            if e.get("route") == "human_mode":
                hs = (all_handoffs or {}).get(st["conv"]) or [handoffs.get(st["conv"]) or {}]
                appended = any(spec["customer"] in h.get("thread_appends", []) for h in hs)
                tally("human_mode_silent", not r.get("reply") and appended)
                if r.get("reply") or not appended:
                    whys.append(f"'{spec['customer']}' in human mode: {'bot replied' if r.get('reply') else 'not in the Slack thread'}")
            for g in e.get("must_include", []):
                if not any(grading.contains(r.get("reply") or "", alt) for alt in g):
                    whys.append(f"missing one of {g}")
            if e.get("route") == "answer":
                tally("close_returns", r.get("route") == "answer")
        if "agent_reply" in spec:
            if c["channel"] == "whatsapp":
                hits = [s for s in rec["wa_sends"] if (s["body"].get("text") or {}).get("body") == spec["agent_reply"]
                        and s["body"].get("to") == e.get("to")]
            else:
                hits = [o for o in outbox if o.get("conversation_id") == st["conv"] and o.get("text") == spec["agent_reply"]]
            ok = len(hits) == 1
            tally("agent_reply_exact", ok)
            if not ok:
                whys.append(f"agent reply delivered {len(hits)} times")
    return whys


# ---------------- commands ----------------

def cmd_run(a):
    env, kb = load_env(), grading.load_kb()
    cases = load_cases(a.data)
    if a.only:
        keep = set(a.only.split(","))
        cases = [c for c in cases if c["id"] in keep]
    bot = Bot(env, a.label)
    bot.reset()
    wa_reset()
    t0 = time.time()
    records = []
    for c in cases:
        records.append(play(bot, c))
        print(f"  sent {c['id']}", flush=True)
    time.sleep(3)
    report = bot.report()
    graded, crit, metrics = grade_run(cases, records, report, kb)
    summary = {"label": a.label, "date": time.strftime("%Y-%m-%d %H:%M"), "seconds": round(time.time() - t0),
               "cases": len(cases), "hold_out": bool(a.data), "only": a.only or None, "critical_case_runs": crit,
               **build_record(report),
               "code_metrics": metrics, "cases_result": {k: {"passed": v["passed"], "misses": v["misses"]}
                                                          for k, v in graded.items()},
               "groups": {c["id"]: c["group"] for c in cases}}
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "raw").mkdir(exist_ok=True)
    (ROOT / "results" / f"{a.label}.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
    (ROOT / "results" / "raw" / f"{a.label}.json").write_text(
        json.dumps({"records": records, "report": report}, indent=1, ensure_ascii=False), encoding="utf-8")
    rate = [k for k, g in summary["groups"].items() if g == "rate"]
    print(f"{a.label}: {sum(graded[k]['passed'] for k in rate)}/{len(rate)} rate cases passed, "
          f"critical case-runs {crit}; code metrics: " +
          ", ".join(f"{m} {v[1]}/{v[2]}" for m, v in metrics.items() if v[2]))
    return 0


def build_record(report):
    """v6 (second and third red teams, finding 12): what each run ran on: a run ID, the local workflow files' hash,
    whether n8n runs exactly those files (checked at the end of the run), the git commit, whether workflows/, tests/
    (run results excepted) or the eval config had uncommitted or new files, and the models in the log rows."""
    import subprocess
    import uuid
    import check_n8n_workflows as cnw
    git = lambda *a: subprocess.run(["git", "-C", str(ROOT.parent), *a], capture_output=True, text=True).stdout.strip()
    try:
        n8n_problems = cnw.live_problems()
    except Exception as e:  # noqa: BLE001 - recorded, and score() then calls the run invalid
        n8n_problems = [f"check failed: {type(e).__name__}"]
    return {"run_id": uuid.uuid4().hex, "workflows_hash": cnw.workflow_hash(cnw.local_docs()),
            "n8n_matches": not n8n_problems, "git_commit": git("rev-parse", "HEAD"),
            "git_dirty": bool(git("status", "--porcelain", "--", "workflows", "tests", "evals/eval_config.yaml",
                                  ":(exclude)tests/results")),
            "models": sorted({r.get("model") for r in report.get("log", []) if r.get("model")})}


def score(summaries, thresholds, holdout2_cases=None, holdout_seen_cases=None):
    """Gate verdict over runs (list of summary dicts). Pure function; tested in tests/test_runner.py.
    v5 (red team 21): every run has the same case IDs and no --only filter; with holdout2_cases (the count in
    evals/holdout2_commitment.json) every run holds exactly that many HN- cases; a code metric with 0 items fails.
    v6 (second and third red teams, finding 12): every run has its own label and run ID, the same recorded
    workflow hash, git commit and models (none missing), n8n ran those workflows, and no tracked file had
    uncommitted changes; with holdout_seen_cases every run holds that many HO- cases; a code metric missing from a
    run fails."""
    groups = summaries[0]["groups"]
    setup = []
    if any(set(s["groups"]) != set(groups) for s in summaries):
        setup.append("runs differ in their case IDs")
    if any(s.get("only") for s in summaries):
        setup.append("a run used --only")
    if holdout2_cases is not None and sum(1 for k in groups if k.startswith("HN-")) != holdout2_cases:
        setup.append(f"hold-out 2 cases in the runs: {sum(1 for k in groups if k.startswith('HN-'))}, commitment: {holdout2_cases}")
    if holdout_seen_cases is not None and sum(1 for k in groups if k.startswith("HO-")) != holdout_seen_cases:
        setup.append(f"hold-out (seen) cases in the runs: {sum(1 for k in groups if k.startswith('HO-'))}, expected: {holdout_seen_cases}")
    for key, what in (("label", "run label"), ("run_id", "run ID")):
        if any(not s.get(key) for s in summaries) or len({s.get(key) for s in summaries}) != len(summaries):
            setup.append(f"a {what} is missing or used twice")
    for key, what in (("workflows_hash", "workflow version"), ("git_commit", "git commit"), ("models", "model list")):
        if any(not s.get(key) for s in summaries) or len({json.dumps(s.get(key)) for s in summaries}) > 1:
            setup.append(f"the {what} is not recorded or differs between runs")
    if any(s.get("n8n_matches") is not True for s in summaries):
        setup.append("n8n did not run the recorded workflows (or it was not checked)")
    if any(s.get("git_dirty") is not False for s in summaries):
        setup.append("a run was made with uncommitted changes (or it was not recorded)")
    rate = [k for k, g in groups.items() if g == "rate"]
    misses = [k for k in rate if not all(s["cases_result"].get(k, {}).get("passed") for s in summaries)]
    crit = sum(s["critical_case_runs"] for s in summaries)
    code_bad = sorted({m for s in summaries for m, v in s["code_metrics"].items() if not v[2] or v[1] != v[2]} |
                      {m for s in summaries for m in CODE_METRICS if m not in s["code_metrics"]})
    changed = sorted(k for k in groups if len({s["cases_result"].get(k, {}).get("passed") for s in summaries}) > 1)
    if setup:
        verdict = "INVALID RUN"
    elif len(rate) < thresholds["rate_cases_min"]:
        verdict = "NOT ENOUGH CASES"
    elif crit == 0 and len(misses) <= thresholds["rate_misses_max"] and not code_bad and len(summaries) == 3:
        verdict = "PASS"
    else:
        verdict = "FAIL"
    return {"verdict": verdict, "rate_cases": len(rate), "rate_passed": len(rate) - len(misses),
            "rate_misses": misses, "critical_case_runs": crit, "code_metrics_below_1": code_bad,
            "changed_between_runs": changed, "setup_problems": setup}


def cmd_score(a):
    import yaml
    th = yaml.safe_load((ROOT.parent / "evals" / "eval_config.yaml").read_text(encoding="utf-8"))["thresholds"]
    sums = [json.loads((ROOT / "results" / f"{l}.json").read_text(encoding="utf-8")) for l in a.labels]
    commit = ROOT.parent / "evals" / "holdout2_commitment.json"
    h2 = json.loads(commit.read_text(encoding="utf-8"))["case_count"] if commit.exists() else None
    seen = len(json.loads((ROOT / "holdout" / "cases.json").read_text(encoding="utf-8"))["cases"])
    r = score(sums, th, h2, seen)
    print(json.dumps(r, indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--label", required=True)
    r.add_argument("--only")
    r.add_argument("--data", action="append", help="folder with a cases.json added to the visible set; repeatable")
    s = sub.add_parser("score")
    s.add_argument("--labels", nargs="+", required=True)
    a = ap.parse_args()
    sys.exit(cmd_run(a) if a.cmd == "run" else cmd_score(a))


if __name__ == "__main__":
    main()
