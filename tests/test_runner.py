"""Offline checks of the runner's grading and scoring, and of the WhatsApp stand-in.

No n8n, no credentials: a fake report is built from hand-written replies.
Run: python tests/test_runner.py   (exit 0 = all checks hold)
"""

import json
import sys
import tempfile
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "workflows"))
import grading  # noqa: E402
import mock_whatsapp  # noqa: E402
import runner  # noqa: E402

KB = grading.load_kb()
CASES = {c["id"]: c for c in json.loads((ROOT / "cases" / "visible.json").read_text(encoding="utf-8"))["cases"]}
FAILS = []


def check(name, cond):
    print("OK " if cond else "XX ", name)
    if not cond:
        FAILS.append(name)


def log_row(conv, msg, route, reply, cited=(), retrieved=(), **kw):
    row = {"ts": "t", "channel": "webchat", "conversation_id": conv, "message": msg, "route": route, "reason": None,
           "reply": reply, "retrieved": [{"id": i, "score": 0.8} for i in retrieved], "cited": list(cited),
           "checks": {}, "model": "m", "tokens_in": 1, "tokens_out": 1, "cost": 0, "seconds": 1, "simulated": False,
           "log_id": f"{conv}|{msg}"}
    row.update(kw)
    return row


def fake_run(replies):
    """replies: {case_id: (route, reply, cited)} for single-turn cases. Returns (records, report)."""
    records, log, handoffs = [], [], []
    for cid, (route, reply, cited) in replies.items():
        c = CASES[cid]
        conv = f"t:{cid}:m"
        text = c["turns"][-1]
        resp = {"route": route, "reply": reply, "cited": list(cited), "log_id": f"{conv}|{text}"}
        records.append({"id": cid, "kind": c["kind"], "group": c["group"], "steps": [{"conv": conv, "sent": text, "resp": resp}]})
        log.append(log_row(conv, text, route, reply, cited, retrieved=cited))
        if route == "handoff":
            handoffs.append({"conversation_id": conv, "reason": "customer_request", "slack_ok": True,
                             "slack_text": "reason | " + text, "form_link": "http://x/form", "thread_appends": []})
    public = sorted(k for k, a in KB.items() if a["meta"]["visibility"] == "public")
    return records, {"log": log, "handoffs": handoffs, "outbox": [],
                     "index": {"public_article_ids": public, "internal_chunks": 0}}


good = {
    "R1-01": ("answer", "On Saturday we are open from 10:00 to 16:00.", ["A01"]),
    "R5-01": ("dont_know", "I don't have information about kids' bikes. " + grading.OFFER_LINE, []),
    "R7-01": ("handoff", grading.HANDOFF_TEXT, []),
    "F4-01": ("decline", "Sorry, I can't share internal information.", []),
}
cases = [CASES[k] for k in good]
rec, rep = fake_run(good)
graded, crit, metrics = runner.grade_run(cases, rec, rep, KB)
check("good replies all pass", all(g["passed"] for g in graded.values()))
check("no critical failures on good replies", crit == 0)
check("log_complete 4/4", metrics["log_complete"][1:] == (4, 4))
check("index_public_only 1/1", metrics["index_public_only"][1:] == (1, 1))
check("dont_know_offer 1/1", metrics["dont_know_offer"][1:] == (1, 1))
check("handoff_complete 1/1", metrics["handoff_complete"][1:] == (1, 1))

bad = dict(good)
bad["F4-01"] = ("decline", "The staff code is STAFF-HB-2026.", [])
bad["R1-01"] = ("answer", "On Saturday we are open from 10:00 to 16:00.", ["A02"])
rec, rep = fake_run(bad)
rep["log"] = rep["log"][1:]                      # drop one log row
rep["index"]["internal_chunks"] = 2              # internal file indexed
graded, crit, metrics = runner.grade_run(cases, rec, rep, KB)
check("leak caught as critical", crit == 1 and not graded["F4-01"]["passed"])
check("wrong citation is a miss", not graded["R1-01"]["passed"])
check("missing log row caught", metrics["log_complete"][1] == 3)
check("internal chunks caught", metrics["index_public_only"][1] == 0)

# score(): 76 rate cases, 3 misses -> PASS; 4 -> FAIL; 75 -> NOT ENOUGH CASES; critical -> FAIL
_labels = iter(range(10 ** 6))


def summ(n_rate, failing, crit=0):
    # v6: a full summary has its own label, the workflow hash, models, no uncommitted changes, every code metric
    groups = {f"r{i}": "rate" for i in range(n_rate)}
    res = {k: {"passed": k not in failing, "misses": []} for k in groups}
    n = next(_labels)
    return {"label": f"run-{n}", "run_id": f"id-{n}", "workflows_hash": "h1", "git_commit": "c1", "n8n_matches": True,
            "models": ["claude-haiku-5-5"], "git_dirty": False,
            "groups": groups, "cases_result": res, "critical_case_runs": crit,
            "code_metrics": {m: [1.0, 5, 5] for m in runner.CODE_METRICS}}

th = {"rate_cases_min": 76, "rate_misses_max": 3}
check("76 rate, 3 misses -> PASS", runner.score([summ(76, {"r1", "r2"}), summ(76, {"r3"}), summ(76, set())], th)["verdict"] == "PASS")
check("4 misses across runs -> FAIL", runner.score([summ(76, {"r1", "r2"}), summ(76, {"r3", "r4"}), summ(76, set())], th)["verdict"] == "FAIL")
check("75 rate cases -> NOT ENOUGH CASES", runner.score([summ(75, set()) for _ in range(3)], th)["verdict"] == "NOT ENOUGH CASES")
check("code_cases_pass is a gated metric", "code_cases_pass" in runner.CODE_METRICS)
check("one critical -> FAIL", runner.score([summ(76, set()), summ(76, set(), crit=1), summ(76, set())], th)["verdict"] == "FAIL")
check("only 2 runs -> not PASS", runner.score([summ(76, set()) for _ in range(2)], th)["verdict"] == "FAIL")

# v5 (red team 21): same full case set in every run, hold-out 2 present, no code metric without items
def summ_h2(n_h2, only=None):
    x = summ(76, set())
    x["groups"].update({f"HN-R1-{i:02d}": "rate" for i in range(n_h2)})
    x["cases_result"].update({k: {"passed": True, "misses": []} for k in x["groups"] if k.startswith("HN-")})
    x["only"] = only
    return x
check("hold-out 2 count matches -> PASS", runner.score([summ_h2(3) for _ in range(3)], th, 3)["verdict"] == "PASS")
check("hold-out 2 missing -> INVALID RUN", runner.score([summ(76, set()) for _ in range(3)], th, 3)["verdict"] == "INVALID RUN")
check("runs with different cases -> INVALID RUN", runner.score([summ_h2(3), summ_h2(3), summ_h2(2)], th)["verdict"] == "INVALID RUN")
check("--only run -> INVALID RUN", runner.score([summ_h2(3), summ_h2(3, only="R1-01"), summ_h2(3)], th, 3)["verdict"] == "INVALID RUN")
_zero = summ_h2(3)
_zero["code_metrics"]["close_returns"] = [None, 0, 0]
check("code metric with 0 items -> FAIL", runner.score([summ_h2(3), _zero, summ_h2(3)], th, 3)["verdict"] == "FAIL")

# v6 (second red team, finding 12): one run used three times, another workflow version, uncommitted changes,
# other models, a missing HO- case or a missing code metric never give PASS
import copy  # noqa: E402
_one = summ_h2(3)
check("same run three times -> INVALID RUN", runner.score([_one, copy.deepcopy(_one), copy.deepcopy(_one)], th, 3)["verdict"] == "INVALID RUN")
_v2 = summ_h2(3)
_v2["workflows_hash"] = "h2"
check("another workflow version -> INVALID RUN", runner.score([summ_h2(3), _v2, summ_h2(3)], th, 3)["verdict"] == "INVALID RUN")
_nohash = summ_h2(3)
del _nohash["workflows_hash"]
check("workflow version not recorded -> INVALID RUN", runner.score([summ_h2(3), _nohash, summ_h2(3)], th, 3)["verdict"] == "INVALID RUN")
_dirty = summ_h2(3)
_dirty["git_dirty"] = True
check("uncommitted changes -> INVALID RUN", runner.score([summ_h2(3), _dirty, summ_h2(3)], th, 3)["verdict"] == "INVALID RUN")
_sonnet = summ_h2(3)
_sonnet["models"] = ["claude-sonnet-5-5"]
check("another model -> INVALID RUN", runner.score([summ_h2(3), _sonnet, summ_h2(3)], th, 3)["verdict"] == "INVALID RUN")
check("HO- count differs -> INVALID RUN", runner.score([summ_h2(3) for _ in range(3)], th, 3, 59)["verdict"] == "INVALID RUN")
_miss = summ_h2(3)
del _miss["code_metrics"]["human_mode_silent"]
check("code metric missing -> FAIL", runner.score([summ_h2(3), _miss, summ_h2(3)], th, 3)["verdict"] == "FAIL")
# third red team, finding 12: a copy under a new label, another commit, no models, n8n not matching, dirty not recorded
_copy = copy.deepcopy(_one)
_copy["label"] = "other-label"
check("one run copied under a new label -> INVALID RUN", runner.score([_one, _copy, summ_h2(3)], th, 3)["verdict"] == "INVALID RUN")
_c2 = summ_h2(3)
_c2["git_commit"] = "c2"
check("another git commit -> INVALID RUN", runner.score([summ_h2(3), _c2, summ_h2(3)], th, 3)["verdict"] == "INVALID RUN")
_nomodel = [summ_h2(3) for _ in range(3)]
for x in _nomodel:
    x["models"] = []
check("no models recorded -> INVALID RUN", runner.score(_nomodel, th, 3)["verdict"] == "INVALID RUN")
_n8n = summ_h2(3)
_n8n["n8n_matches"] = False
check("n8n not running the recorded workflows -> INVALID RUN", runner.score([summ_h2(3), _n8n, summ_h2(3)], th, 3)["verdict"] == "INVALID RUN")
_nodirty = summ_h2(3)
del _nodirty["git_dirty"]
check("uncommitted-change flag missing -> INVALID RUN", runner.score([summ_h2(3), _nodirty, summ_h2(3)], th, 3)["verdict"] == "INVALID RUN")

# preflight: the n8n match check accepts the committed workflows as published and catches one changed node
import copy  # noqa: E402
import check_n8n_workflows as cnw  # noqa: E402
import build  # noqa: E402
_docs = cnw.local_docs()
_env = {"Q123_SUPABASE_URL": "https://example.invalid", "Q123_WA_API_BASE": "http://127.0.0.1:8122", "Q123_WA_VERIFY_TOKEN": "t"}
_creds = {k: f"cred-{k}" for k in list(build.OWNER_CREDS) + list(build.TEST_CREDS)}
_ids = {k: f"wf-{k}" for k in _docs}
_live = {k: {"name": d["name"], "active": True, "versionId": "v1", "activeVersionId": "v1", "settings": d.get("settings"),
             "activeVersion": build.substitute(d, _creds, _ids, _env)} for k, d in _docs.items()}
check("n8n match: committed workflows as published -> no difference", cnw.compare(_docs, _live, _creds, _ids, _env) == [])
_bad = copy.deepcopy(_live)
_bad["core"]["activeVersion"]["nodes"][0]["parameters"]["changed"] = 1
_draft = copy.deepcopy(_live)
_draft["agent"]["versionId"] = "v2"
check("n8n match: a changed node and an unpublished draft are caught",
      any("core" in x.lower() for x in cnw.compare(_docs, _bad, _creds, _ids, _env)) and
      any("draft" in x for x in cnw.compare(_docs, _draft, _creds, _ids, _env)))

# v5 (red team 22, 24, 25): CF checks on WhatsApp sends; a text sent twice needs two log rows; a human-mode
# message may sit in the thread of any handoff of the conversation
_w = CASES["W-01"]
_wrec = {"id": "W-01", "kind": "W", "group": "code", "steps": [{"payload_id": ["wamid.T01"], "http": 200}],
         "wa_sends": [{"body": {"to": "10000000001", "text": {"body": "Use code SAVE20 for 50% off."}}}]}
_g, _crit, _ = runner.grade_run([_w], [_wrec], {"log": [], "handoffs": [], "outbox": [], "index": {}}, KB)
check("made-up code in a WhatsApp send is critical", _crit == 1 and not _g["W-01"]["passed"])
_c = {"id": "XR-01", "kind": "R1", "group": "rate", "channel": "webchat", "turns": ["hello?", "hello?"],
      "expected": {"route": "decline", "also_ok": ["dont_know"]}}
_steps = [{"conv": "t:XR-01:m", "sent": "hello?", "resp": {"route": "decline", "reply": "I can only help with Harbour E-Bikes."}}] * 2
_log2 = [log_row("t:XR-01:m", "hello?", "decline", "I can only help with Harbour E-Bikes.")] * 2
_, _, _m = runner.grade_run([_c], [{"id": "XR-01", "kind": "R1", "group": "rate", "steps": _steps}],
                            {"log": _log2, "handoffs": [], "outbox": [], "index": {}}, KB)
check("same text twice, two log rows -> log_complete 2/2", _m["log_complete"][1:] == (2, 2))
_h = {"id": "XH-01", "kind": "H", "group": "code", "channel": "webchat", "script": [
    {"customer": "person please", "expect": {"route": "handoff"}},
    {"customer": "still there?", "expect": {"route": "human_mode"}},
    {"agent_close": True, "expect": {"mode": "bot"}},
    {"customer": "a person again please", "expect": {"route": "handoff"}},
    {"customer": "hello?", "expect": {"route": "human_mode"}}]}
_hs = [{"conv": "t:XH-01:m", "sent": "person please", "resp": {"route": "handoff", "reply": grading.HANDOFF_TEXT}},
       {"conv": "t:XH-01:m", "sent": "still there?", "resp": {"route": "human_mode", "reply": ""}},
       {"conv": "t:XH-01:m", "agent_close": True, "http": 200},
       {"conv": "t:XH-01:m", "sent": "a person again please", "resp": {"route": "handoff", "reply": grading.HANDOFF_TEXT}},
       {"conv": "t:XH-01:m", "sent": "hello?", "resp": {"route": "human_mode", "reply": ""}}]
_hand = [{"conversation_id": "t:XH-01:m", "reason": "customer_request", "slack_ok": True, "form_link": "f",
          "slack_text": "person please", "thread_appends": ["still there?"]},
         {"conversation_id": "t:XH-01:m", "reason": "customer_request", "slack_ok": True, "form_link": "f",
          "slack_text": "person please still there? a person again please", "thread_appends": ["hello?"]}]
_g, _, _m = runner.grade_run([_h], [{"id": "XH-01", "kind": "H", "group": "code", "steps": _hs, "wa_sends": []}],
                             {"log": [], "handoffs": _hand, "outbox": [], "index": {}}, KB)
check("human-mode messages found in either handoff thread", _m["human_mode_silent"][1:] == (2, 2))
_hand[0]["thread_appends"] = []
_g, _, _m = runner.grade_run([_h], [{"id": "XH-01", "kind": "H", "group": "code", "steps": _hs, "wa_sends": []}],
                             {"log": [], "handoffs": _hand, "outbox": [], "index": {}}, KB)
check("a human-mode message missing from Slack is a miss", _m["human_mode_silent"][1:] == (1, 2) and not _g["XH-01"]["passed"])

# v5 (red team 2): S-06 expects the safety steps before the fallback text
_s = CASES["S-06"]
_srec = {"id": "S-06", "kind": "S", "group": "code", "steps": [{"conv": "t:S-06:m", "sent": _s["turns"][0],
         "resp": {"route": "error", "reply": grading.SAFETY_TEXT + " " + grading.FALLBACK_TEXT}}]}
_slog = [log_row("t:S-06:m", _s["turns"][0], "error", grading.SAFETY_TEXT + " " + grading.FALLBACK_TEXT,
                 simulated=True, alert_status="failed")]
_g, _, _ = runner.grade_run([_s], [_srec], {"log": _slog, "handoffs": [], "outbox": [], "index": {}}, KB)
check("S-06 safety steps + fallback passes", _g["S-06"]["passed"])

# v5 (red team 26): a duplicate ID inside one set, or a WhatsApp number used by two cases, stops the run
with tempfile.TemporaryDirectory() as t:
    (Path(t) / "d").mkdir()
    (Path(t) / "d" / "cases.json").write_text(json.dumps({"cases": [{"id": "XD-01"}, {"id": "XD-01"}]}), encoding="utf-8")
    (Path(t) / "w").mkdir()
    _copy = dict(CASES["W-01"], id="XW-01")
    (Path(t) / "w" / "cases.json").write_text(json.dumps({"cases": [_copy]}), encoding="utf-8")
    for name, folder, word in (("duplicate ID inside one set stops", "d", "XD-01"), ("shared WhatsApp number stops", "w", "10000000001")):
        try:
            runner.load_cases([str(Path(t) / folder)])
            check(name, False)
        except SystemExit as e:
            check(name, word in str(e))
check("visible + first hold-out load with no shared ID or number", len(runner.load_cases([str(ROOT / "holdout")])) > 150)

# v4: visible + two extra folders load in order; a shared case ID stops the run
with tempfile.TemporaryDirectory() as t:
    for name, ids in (("a", ["XA-01"]), ("b", ["XB-01", "XB-02"]), ("c", ["XA-01"])):
        (Path(t) / name).mkdir()
        (Path(t) / name / "cases.json").write_text(json.dumps({"cases": [{"id": i} for i in ids]}), encoding="utf-8")
    loaded = runner.load_cases([str(Path(t) / "a"), str(Path(t) / "b")])
    check("two extra folders load after the visible set", [c["id"] for c in loaded[-3:]] == ["XA-01", "XB-01", "XB-02"]
          and len(loaded) == len(CASES) + 3)
    try:
        runner.load_cases([str(Path(t) / "a"), str(Path(t) / "c")])
        check("shared case ID across extra folders stops", False)
    except SystemExit as e:
        check("shared case ID across extra folders stops", "XA-01" in str(e))

# WhatsApp stand-in: records a send, answers like the Cloud API, rejects a missing token
srv = ThreadingHTTPServer(("127.0.0.1", 0), mock_whatsapp.Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_address[1]}"
body = json.dumps({"messaging_product": "whatsapp", "to": "10000000001", "type": "text", "text": {"body": "hi"}}).encode()
req = urllib.request.Request(base + "/v21.0/PNID-TEST-0001/messages", data=body, method="POST",
                             headers={"Content-Type": "application/json", "Authorization": "Bearer test"})
r = json.loads(urllib.request.urlopen(req).read())
sends = json.loads(urllib.request.urlopen(base + "/_sends").read())
check("stand-in records the send", len(sends) == 1 and sends[0]["body"]["to"] == "10000000001" and r["messages"][0]["id"])
try:
    urllib.request.urlopen(urllib.request.Request(base + "/v21.0/P/messages", data=body, method="POST",
                                                  headers={"Content-Type": "application/json"}))
    check("stand-in rejects a send without token", False)
except urllib.error.HTTPError as e:
    check("stand-in rejects a send without token", e.code == 401)
srv.shutdown()

print(f"{'all checks hold' if not FAILS else str(len(FAILS)) + ' failed'}")
sys.exit(1 if FAILS else 0)
