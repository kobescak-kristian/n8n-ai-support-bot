"""Offline checks of the runner's grading and scoring, and of the WhatsApp stand-in.

No n8n, no credentials: a fake report is built from hand-written replies.
Run: python tests/test_runner.py   (exit 0 = all checks hold)
"""

import json
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
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
def summ(n_rate, failing, crit=0):
    groups = {f"r{i}": "rate" for i in range(n_rate)}
    res = {k: {"passed": k not in failing, "misses": []} for k in groups}
    return {"groups": groups, "cases_result": res, "critical_case_runs": crit, "code_metrics": {"log_complete": [1.0, 5, 5]}}

th = {"rate_cases_min": 76, "rate_misses_max": 3}
check("76 rate, 3 misses -> PASS", runner.score([summ(76, {"r1", "r2"}), summ(76, {"r3"}), summ(76, set())], th)["verdict"] == "PASS")
check("4 misses across runs -> FAIL", runner.score([summ(76, {"r1", "r2"}), summ(76, {"r3", "r4"}), summ(76, set())], th)["verdict"] == "FAIL")
check("75 rate cases -> NOT ENOUGH CASES", runner.score([summ(75, set())] * 3, th)["verdict"] == "NOT ENOUGH CASES")
check("code_cases_pass is a gated metric", "code_cases_pass" in runner.CODE_METRICS)
check("one critical -> FAIL", runner.score([summ(76, set()), summ(76, set(), crit=1), summ(76, set())], th)["verdict"] == "FAIL")
check("only 2 runs -> not PASS", runner.score([summ(76, set())] * 2, th)["verdict"] == "FAIL")

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
