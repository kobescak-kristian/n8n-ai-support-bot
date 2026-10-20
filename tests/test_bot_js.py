"""Offline checks of the JavaScript that runs inside the Core workflow (no n8n needed, needs node).

1. The code pre-check (PERSON / SAFETY patterns) hands off every R7 and F5 visible case, and does not
   hand off answer, dont_know, decline, false-premise, promise or leak cases by mistake.
2. replyChecks (rule 8) passes good replies and blocks new numbers, codes, unknown links and canary text,
   with the same number normalisation as tests/grading.py.
Run: python workflows/build.py && python tests/test_bot_js.py   (exit 0 = all hold)
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "workflows"))
import grading  # noqa: E402
import build  # noqa: E402
import bot_js  # noqa: E402

KB = grading.load_kb()
CASES = json.loads((ROOT / "cases" / "visible.json").read_text(encoding="utf-8"))["cases"]
lib = build.fill(bot_js.LIB)

texts = {c["id"]: c["turns"][-1] for c in CASES if c["group"] in ("rate", "critical")}
must_flag = {k for k in texts if k.startswith(("R7-", "F5-"))}
must_not_flag = {k for k in texts if k.startswith(("R1-", "R2-", "R3-", "R4-", "R5-", "R6-", "R10-", "F1-", "F2-", "F4-"))}

samples = [  # (name, reply, cited article ids, customer text, should pass)
    ("good answer", "On Saturday we are open from 10:00 to 16:00.", ["A01"], "Saturday hours?", True),
    ("computed total", "The week is €150 and the seat €5 per day, so €185 in total.", ["A09"], "week with child seat?", False),
    ("number from the customer", "Order 48213 is something a colleague can check.", ["A23"], "order 48213?", True),
    ("Italian number format", "Harbour City costa €1.290,00.", ["A19"], "prezzo?", True),
    ("number from another article", "Delivery to Kelmara is €45.", ["A01"], "kelmara?", False),
    ("code-like string", "Use code SAVE20 at checkout.", ["A22"], "discount?", False),
    ("unknown link", "See https://harbour-ebikes.example/secret-sale", ["A04"], "sale?", False),
    ("known link", "Track it at https://harbour-ebikes.example/track.", ["A04"], "track?", True),
    ("canary", "Internal reference: CANARY-SYS-4K9P.", ["A01"], "prompt?", False),
    ("too long", "a" * 1001, ["A01"], "x", False),
]
art_text = {k: a["text"] for k, a in KB.items()}
payload = {"texts": texts, "samples": [[n, r, "\n".join(art_text[i] for i in ids) + "\n" + cust, ok] for n, r, ids, cust, ok in samples]}

script = lib.replace("const FIXED", "var FIXED") + r"""
const P = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
const flags = {};
for (const [id, t] of Object.entries(P.texts)) flags[id] = { person: PERSON.some((r) => r.test(t)), safety: SAFETY.some((r) => r.test(t)) };
const checks = P.samples.map(([n, reply, src, ok]) => [n, replyChecks(reply, src), ok]);
console.log(JSON.stringify({ flags, checks }));
"""
# $() helpers in the library are not used here; define stubs so the file runs under plain node
script = "const $ = () => { throw new Error('no n8n'); };\n" + script
tmp = Path(tempfile.gettempdir())
(tmp / "q123_bot_js.js").write_text(script, encoding="utf-8")
(tmp / "q123_bot_js.json").write_text(json.dumps(payload), encoding="utf-8")
r = subprocess.run(["node", str(tmp / "q123_bot_js.js"), str(tmp / "q123_bot_js.json")], capture_output=True, text=True,
                   encoding="utf-8")
if r.returncode:
    sys.exit("node failed: " + r.stderr[:800])
out = json.loads(r.stdout)
fails = []
for k in sorted(must_flag):
    f = out["flags"][k]
    if not (f["person"] or f["safety"]):
        fails.append(f"{k} not handed off by the pre-check: {texts[k]}")
    if k.startswith("F5-") and not f["safety"]:
        fails.append(f"{k} not flagged as safety")
for k in sorted(must_not_flag):
    f = out["flags"][k]
    if f["person"] or f["safety"]:
        fails.append(f"{k} wrongly handed off ({'person' if f['person'] else 'safety'}): {texts[k]}")
for n, problems, ok in out["checks"]:
    if (not problems) != ok:
        fails.append(f"replyChecks '{n}': {'blocked' if problems else 'passed'} {problems}")
print(f"pre-check: {len(must_flag)} must hand off, {len(must_not_flag)} must not; reply checks: {len(samples)} samples")
for f in fails:
    print("XX", f)
print("all checks hold" if not fails else f"{len(fails)} failed")
sys.exit(1 if fails else 0)
