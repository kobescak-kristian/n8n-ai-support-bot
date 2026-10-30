"""Send the knowledge base to the index workflow.

Posts EVERY file in tests/kb/ (the internal I01 too): the workflow itself must keep only
visibility: public (CASES.md rule 9), and the report checks that it did.
Run: python tools/index_kb.py   (needs n8n running, the bot workflows and Q123_WEBHOOK_KEY in .env)
"""
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "tools"))
import grading  # noqa: E402
from n8n_api import load_env  # noqa: E402

kb = grading.load_kb()
arts = [{"id": k, "title": a["meta"]["title"], "visibility": a["meta"]["visibility"], "updated": a["meta"]["updated"],
         "status": a["meta"].get("status", "current"), "text": a["text"].split("\n", 1)[1]} for k, a in kb.items()]
req = urllib.request.Request("http://localhost:5678/webhook/q123-index", data=json.dumps({"articles": arts}).encode("utf-8"),
                             method="POST", headers={"Content-Type": "application/json",
                                                     "X-Webhook-Key": load_env().get("Q123_WEBHOOK_KEY", "")})
with urllib.request.urlopen(req, timeout=180) as r:
    out = json.loads(r.read())
print(out)
sys.exit(0 if out.get("indexed") == sum(a["visibility"] == "public" for a in arts) else 1)
