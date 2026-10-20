"""Generate and load the n8n workflows of the AI support bot (Q-123).

python workflows/build.py           -> workflows/*.json (placeholders: no credential IDs, no Supabase URL, no secrets)
python workflows/build.py --push    -> also creates the test-only credentials from the git-ignored .env (webhook keys,
                                       form login, WhatsApp test token and app secret), creates/updates every Q123
                                       workflow in local n8n through the n8n API, fills credential and workflow IDs by
                                       name, and publishes them. Owner-made credentials (Anthropic, OpenAI, Supabase,
                                       Slack) must already exist with their standard names.

Shared n8n: only Q123-prefixed workflows, q123_* data tables and /webhook/q123-* paths. Never restarts or
reconfigures n8n. The workflow logic lives here and in bot_js.py; the JSON files are build output.
"""
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "workflows"
sys.path.insert(0, str(OUT))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import bot_js as J  # noqa: E402
import grading  # noqa: E402

BASE = "http://localhost:5678"
import os
MODEL = os.environ.get("Q123_MODEL", "claude-haiku-5-5")   # chosen by the model check (evals/model_check.yaml, RESULTS mc-*)
FLOOR = 0.20                  # logged only (visible-1: a floor shortcut skipped Claude and missed a complaint, R9-03)
SLACK_CHANNEL = "#support-handoff"
SHORT = "n8n-ai-support-bot"
OWNER_CREDS = {"anthropicApi": f"Anthropic {SHORT}", "openAiApi": f"OpenAI {SHORT}",
               "supabaseApi": f"Supabase {SHORT}", "slackApi": f"Slack {SHORT}"}
# test-only credentials created by --push from .env (type, n8n name, data builder)
TEST_CREDS = {
    "webhookKey": ("httpHeaderAuth", f"Webhook {SHORT}", lambda e: {"name": "X-Webhook-Key", "value": e["Q123_WEBHOOK_KEY"]}),
    "formLogin": ("httpBasicAuth", f"Reply form {SHORT}", lambda e: {"user": e["Q123_FORM_USER"], "password": e["Q123_FORM_PASSWORD"]}),
    "waToken": ("httpHeaderAuth", f"WhatsApp {SHORT} (test)", lambda e: {"name": "Authorization", "value": "Bearer " + e["Q123_WA_TEST_TOKEN"]}),
    "waSecret": ("crypto", f"WhatsApp app secret {SHORT} (test)", lambda e: {"hmacSecret": e["Q123_WA_TEST_SECRET"]}),
}
TABLES = {
    "q123_messages": [("conversation_id", "string"), ("role", "string"), ("text", "string"), ("at", "string"),
                      ("run_label", "string")],
    "q123_log": [("log_id", "string"), ("ts", "string"), ("run_label", "string"), ("channel", "string"),
                 ("conversation_id", "string"), ("message_id", "string"), ("message", "string"), ("route", "string"),
                 ("reason", "string"), ("reply", "string"), ("retrieved", "string"), ("cited", "string"),
                 ("checks", "string"), ("model", "string"), ("tokens_in", "number"), ("tokens_out", "number"),
                 ("cost", "number"), ("seconds", "number"), ("simulated", "boolean"), ("ai_called", "boolean"),
                 ("alert_status", "string"), ("mode_after", "string"), ("slack_ok", "boolean"), ("slack_ts", "string"),
                 ("slack_text", "string"), ("form_link", "string"), ("wa_id", "string"), ("phone_number_id", "string")],
    "q123_agent": [("at", "string"), ("run_label", "string"), ("conversation_id", "string"), ("action", "string"),
                   ("text", "string"), ("channel", "string"), ("delivered", "boolean"), ("wa_message_id", "string")],
    "q123_seen": [("message_id", "string"), ("at", "string")],
    "q123_settings": [("run_label", "string"), ("at", "string")],
}


def fill(js):
    fixed = {k: getattr(grading, k) for k in ("OFFER_LINE", "HANDOFF_TEXT", "SAFETY_TEXT", "FALLBACK_TEXT", "MEDIA_TEXT")}
    system = J.SYSTEM_PROMPT.replace("__CANARY_LINE__", grading.SYSTEM_PROMPT_CANARY_LINE)
    return (js.replace("__FIXED__", json.dumps(fixed)).replace("__CANARY_LINE__", json.dumps(grading.SYSTEM_PROMPT_CANARY_LINE))
            .replace("__SYSTEM_PROMPT__", json.dumps(system)).replace("__MODEL__", MODEL).replace("__FLOOR__", str(FLOOR))
            .replace("__SLACK_CHANNEL__", SLACK_CHANNEL).strip() + "\n")


class WF:
    def __init__(self, key, name):
        self.key, self.name = key, name
        self.nodes, self.conn = [], {}

    def add(self, name, ntype, version, params, x, y=0, cred=None, **extra):
        n = {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"q123/{self.key}/{name}")), "name": name, "type": ntype,
             "typeVersion": version, "position": [int(x * 260), int(y * 180)], "parameters": params}
        if cred:
            ctype, ckey = cred
            cname = OWNER_CREDS.get(ckey) or TEST_CREDS[ckey][1]
            n["credentials"] = {ctype: {"id": f"__CRED:{ckey}__", "name": cname}}
        n.update(extra)
        self.nodes.append(n)
        return name

    def link(self, a, b, out=0):
        outs = self.conn.setdefault(a, {"main": []})["main"]
        while len(outs) <= out:
            outs.append([])
        outs[out].append({"node": b, "type": "main", "index": 0})

    def chain(self, *names):
        for a, b in zip(names, names[1:]):
            self.link(a, b)

    def doc(self):
        return {"name": self.name, "nodes": self.nodes, "connections": self.conn, "settings": {"executionOrder": "v1"}}


def code(w, name, js, x, y=0, **extra):
    return w.add(name, "n8n-nodes-base.code", 2, {"jsCode": fill(js)}, x, y, **extra)


def if_true(w, name, expr, x, y=0):
    return w.add(name, "n8n-nodes-base.if", 2.2, {"conditions": {
        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
        "conditions": [{"id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"q123/{w.key}/{name}")), "leftValue": expr,
                        "rightValue": "", "operator": {"type": "boolean", "operation": "true", "singleValue": True}}],
        "combinator": "and"}, "looseTypeValidation": True, "options": {}}, x, y)


def table(name):
    return {"__rl": True, "mode": "name", "value": name}


def insert(w, name, tbl, x, y=0, **extra):
    return w.add(name, "n8n-nodes-base.dataTable", 1.1, {
        "dataTableId": table(tbl),
        "columns": {"mappingMode": "autoMapInputData", "value": {}, "matchingColumns": [], "schema": []},
        "options": {}}, x, y, onError="continueRegularOutput", **extra)


def get_rows(w, name, tbl, x, y=0, key=None, value=None, **extra):
    p = {"operation": "get", "dataTableId": table(tbl), "returnAll": True}
    if key:
        p.update(matchType="allConditions", filters={"conditions": [{"keyName": key, "condition": "eq", "keyValue": value}]})
    return w.add(name, "n8n-nodes-base.dataTable", 1.1, p, x, y, alwaysOutputData=True, executeOnce=True, **extra)


def webhook(w, name, method, path, x, y=0, auth="webhookKey", raw=False):
    p = {"httpMethod": method, "path": path, "responseMode": "responseNode", "options": {"rawBody": True} if raw else {}}
    cred = None
    if auth == "webhookKey":
        p["authentication"] = "headerAuth"
        cred = ("httpHeaderAuth", "webhookKey")
    elif auth == "formLogin":
        p["authentication"] = "basicAuth"
        cred = ("httpBasicAuth", "formLogin")
    return w.add(name, "n8n-nodes-base.webhook", 2.1, p, x, y, cred=cred,
                 webhookId=str(uuid.uuid5(uuid.NAMESPACE_URL, f"q123/{path}/{method}")))


def respond(w, name, body_expr, x, y=0, code_=200, text=False, html=False):
    opts = {"responseCode": code_}
    if html:
        opts["responseHeaders"] = {"entries": [{"name": "Content-Type", "value": "text/html; charset=utf-8"}]}
    return w.add(name, "n8n-nodes-base.respondToWebhook", 1.4,
                 {"respondWith": "text" if (text or html) else "json", "responseBody": body_expr, "options": opts}, x, y)


def http(w, name, x, y=0, cred=None, headers=None, method="POST", throw=False, **extra):
    """Generic HTTP node: URL, JSON body and timeout come from the previous Code node ($json.url/body/timeout_ms)."""
    p = {"method": method, "url": "={{ $json.url }}", "sendBody": method != "GET", "specifyBody": "json",
         "jsonBody": "={{ JSON.stringify($json.body) }}",
         "options": {"timeout": "={{ $json.timeout_ms || 20000 }}",
                     "response": {"response": {"fullResponse": True, "neverError": not throw, "responseFormat": "json"}}}}
    if method == "GET":
        p.pop("specifyBody"), p.pop("jsonBody")
    c = None
    if cred:
        ctype, ckey = cred
        if ctype == "httpHeaderAuth":
            p.update(authentication="genericCredentialType", genericAuthType="httpHeaderAuth")
        else:
            p.update(authentication="predefinedCredentialType", nodeCredentialType=ctype)
        c = cred
    if headers:
        p.update(sendHeaders=True, headerParameters={"parameters": [{"name": k, "value": v} for k, v in headers.items()]})
    return w.add(name, "n8n-nodes-base.httpRequest", 4.2, p, x, y, cred=c, onError="continueRegularOutput", **extra)


def call_core(w, name, x, y=0, each=False):
    return w.add(name, "n8n-nodes-base.executeWorkflow", 1.2, {
        "source": "database", "workflowId": {"__rl": True, "mode": "id", "value": "__WF:core__"},
        "mode": "each" if each else "once", "options": {"waitForSubWorkflow": True}}, x, y)


ANTHROPIC = ("anthropicApi", "anthropicApi")
OPENAI = ("openAiApi", "openAiApi")
SUPABASE = ("supabaseApi", "supabaseApi")
SLACK = ("slackApi", "slackApi")


# ------------------------------------------------------------------------------------------------
def build_core():
    w = WF("core", "Q123 Core: answer one message")
    w.add("Start", "n8n-nodes-base.executeWorkflowTrigger", 1.3, {"inputSource": "passthrough"}, 0)
    get_rows(w, "Load log rows", "q123_log", 1, key="conversation_id", value="={{ $('Start').first().json.conversation_id }}")
    get_rows(w, "Load agent rows", "q123_agent", 2, key="conversation_id", value="={{ $('Start').first().json.conversation_id }}")
    get_rows(w, "Load messages", "q123_messages", 3, key="conversation_id", value="={{ $('Start').first().json.conversation_id }}")
    code(w, "Pre-check", J.PRECHECK, 4, executeOnce=True)
    if_true(w, "Needs AI?", "={{ $json.state.next === 'retrieve' }}", 5)
    code(w, "Prepare embedding", J.PREP_EMBED, 6, -1)
    http(w, "Embed question", 7, -1, cred=OPENAI, throw=True, retryOnFail=True, maxTries=2, waitBetweenTries=2000)
    code(w, "Prepare search", J.PREP_SEARCH, 8, -1)
    http(w, "Search articles", 9, -1, cred=SUPABASE, throw=True, retryOnFail=True, maxTries=2, waitBetweenTries=2000)
    code(w, "Prepare Claude", J.PREP_CLAUDE, 10, -1)
    if_true(w, "Call Claude?", "={{ $json.ok }}", 11, -1)
    http(w, "Call Claude", 12, -2, cred=ANTHROPIC, throw=True, retryOnFail=True, maxTries=2, waitBetweenTries=3000,
         headers={"anthropic-version": "2023-06-01", "anthropic-beta": "server-side-fallback-2026-07-01"})
    code(w, "Finalize", J.FINALIZE, 13)
    if_true(w, "Slack needed?", "={{ !!$json.slack }}", 14)
    code(w, "Prepare Slack", J.PREP_SLACK, 15, -1)
    http(w, "Post to Slack", 16, -1, cred=SLACK, retryOnFail=True, maxTries=2, waitBetweenTries=2000)
    code(w, "After Slack", J.AFTER_SLACK, 17)
    code(w, "Message rows", J.MESSAGE_ROWS, 18)
    insert(w, "Write messages", "q123_messages", 19)
    code(w, "Log row", J.LOG_ROW, 20, executeOnce=True)
    insert(w, "Write log", "q123_log", 21)
    code(w, "Result", J.RESULT, 22, executeOnce=True)
    w.chain("Start", "Load log rows", "Load agent rows", "Load messages", "Pre-check", "Needs AI?")
    w.link("Needs AI?", "Prepare embedding", 0)
    w.link("Needs AI?", "Finalize", 1)
    w.chain("Prepare embedding", "Embed question", "Prepare search", "Search articles", "Prepare Claude", "Call Claude?")
    w.link("Call Claude?", "Call Claude", 0)
    w.link("Call Claude?", "Finalize", 1)
    w.chain("Call Claude", "Finalize", "Slack needed?")
    w.link("Slack needed?", "Prepare Slack", 0)
    w.link("Slack needed?", "After Slack", 1)
    w.chain("Prepare Slack", "Post to Slack", "After Slack", "Message rows", "Write messages", "Log row", "Write log", "Result")
    return w


def build_test_entry():
    w = WF("entry-test", "Q123 Entry: test message")
    webhook(w, "Test message", "POST", "q123-message", 0)
    code(w, "To core input", J.TEST_INPUT, 1)
    call_core(w, "Answer", 2)
    code(w, "Reply", J.TEST_REPLY, 3)
    respond(w, "Send reply", "={{ JSON.stringify($json) }}", 4)
    w.chain("Test message", "To core input", "Answer", "Reply", "Send reply")
    return w


def build_chat_entry():
    w = WF("entry-chat", "Q123 Entry: web chat")
    w.add("Web chat", "@n8n/n8n-nodes-langchain.chatTrigger", 1.1, {
        "public": True, "mode": "hostedChat", "authentication": "basicAuth",
        "initialMessages": "Hi! I'm the Harbour E-Bikes assistant. Ask me about rentals, repairs, delivery or returns.",
        "options": {"responseMode": "lastNode", "title": "Harbour E-Bikes support (demo)"}}, 0,
        cred=("httpBasicAuth", "formLogin"), webhookId=str(uuid.uuid5(uuid.NAMESPACE_URL, "q123/chat")))
    code(w, "To core input", J.CHAT_INPUT, 1)
    call_core(w, "Answer", 2)
    code(w, "To chat", J.CHAT_OUTPUT, 3)
    w.chain("Web chat", "To core input", "Answer", "To chat")
    return w


def build_whatsapp_entry():
    w = WF("entry-whatsapp", "Q123 Entry: WhatsApp")
    # Meta's verify-token handshake (GET); Meta cannot send our own header, so no Header Auth here
    webhook(w, "WhatsApp handshake", "GET", "q123-whatsapp", 0, -2, auth=None)
    code(w, "Check verify token", J.WA_HANDSHAKE, 1, -2)
    w.add("Answer handshake", "n8n-nodes-base.respondToWebhook", 1.4, {
        "respondWith": "text", "responseBody": "={{ $json.challenge }}",
        "options": {"responseCode": "={{ $json.ok ? 200 : 403 }}"}}, 2, -2)
    w.chain("WhatsApp handshake", "Check verify token", "Answer handshake")
    # Messages (POST): signature check on the raw body with the app secret (X-Hub-Signature-256)
    webhook(w, "WhatsApp message", "POST", "q123-whatsapp", 0, 0, auth=None, raw=True)
    w.add("Sign raw body", "n8n-nodes-base.crypto", 2, {
        "action": "hmac", "type": "SHA256", "binaryData": True, "binaryPropertyName": "data",
        "dataPropertyName": "signature", "encoding": "hex"}, 1, 0, cred=("crypto", "waSecret"))
    code(w, "Verify signature", J.WA_VERIFY, 2, executeOnce=True)
    if_true(w, "Signed?", "={{ $json.ok }}", 3)
    respond(w, "Refuse", "={{ JSON.stringify({ error: 'bad signature' }) }}", 4, 1, code_=401)
    get_rows(w, "Seen ids", "q123_seen", 4, -1)
    get_rows(w, "Run label", "q123_settings", 5, -1)
    code(w, "New messages", J.WA_NEW, 6, -1, executeOnce=True)
    if_true(w, "Anything new?", "={{ !$json.none }}", 7, -1)
    respond(w, "Nothing new", "={{ JSON.stringify({ ok: true }) }}", 8, 0)
    code(w, "Seen rows", "return $input.all().map((i) => ({ json: { message_id: i.json.message_id, at: new Date().toISOString() } }));", 8, -1)
    insert(w, "Mark seen", "q123_seen", 9, -1)
    respond(w, "Accept", "={{ JSON.stringify({ ok: true }) }}", 10, -1)
    code(w, "Core input", "return $('New messages').all();", 11, -1, executeOnce=False)
    call_core(w, "Answer", 12, -1, each=True)
    code(w, "Send bodies", J.WA_SEND, 13, -1)
    http(w, "Send WhatsApp", 14, -1, cred=("httpHeaderAuth", "waToken"))
    w.chain("WhatsApp message", "Sign raw body", "Verify signature", "Signed?")
    w.link("Signed?", "Seen ids", 0)
    w.link("Signed?", "Refuse", 1)
    w.chain("Seen ids", "Run label", "New messages", "Anything new?")
    w.link("Anything new?", "Seen rows", 0)
    w.link("Anything new?", "Nothing new", 1)
    w.chain("Seen rows", "Mark seen", "Accept", "Core input", "Answer", "Send bodies", "Send WhatsApp")
    return w


def build_agent():
    w = WF("agent", "Q123 Agent: reply form")
    webhook(w, "Agent page", "GET", "q123-agent", 0, -2, auth="formLogin")
    get_rows(w, "Conversation messages", "q123_messages", 1, -2, key="conversation_id",
             value="={{ String(($('Agent page').first().json.query || {}).c || 'none') }}")
    code(w, "Page", J.AGENT_PAGE, 2, -2, executeOnce=True)
    respond(w, "Show page", "={{ $json.html }}", 3, -2, html=True)
    w.chain("Agent page", "Conversation messages", "Page", "Show page")
    webhook(w, "Agent submit", "POST", "q123-agent-submit", 0, 0, auth="formLogin")
    get_rows(w, "Conversation log", "q123_log", 1, 0, key="conversation_id",
             value="={{ String(($('Agent submit').first().json.body || {}).conversation_id || 'none') }}")
    get_rows(w, "Run label", "q123_settings", 2, 0)
    code(w, "Decide agent action", J.AGENT_DECIDE, 3, executeOnce=True)
    if_true(w, "Valid?", "={{ $json.valid }}", 4)
    respond(w, "Refused", "<p>Nothing sent: unknown conversation or empty reply.</p>", 5, 1, code_=400, html=True)
    if_true(w, "WhatsApp reply?", "={{ $json.action === 'reply' && $json.channel === 'whatsapp' }}", 5)
    http(w, "Send WhatsApp reply", 6, -1, cred=("httpHeaderAuth", "waToken"))
    code(w, "Agent row", J.AGENT_ROW, 7, executeOnce=True)
    insert(w, "Write agent row", "q123_agent", 8)
    respond(w, "Done", "<p>Done. You can close this page.</p>", 9, html=True)
    w.chain("Agent submit", "Conversation log", "Run label", "Decide agent action", "Valid?")
    w.link("Valid?", "WhatsApp reply?", 0)
    w.link("Valid?", "Refused", 1)
    w.link("WhatsApp reply?", "Send WhatsApp reply", 0)
    w.link("WhatsApp reply?", "Agent row", 1)
    w.chain("Send WhatsApp reply", "Agent row", "Write agent row", "Done")
    return w


def build_index():
    w = WF("index", "Q123 Index: knowledge base")
    webhook(w, "Index request", "POST", "q123-index", 0)
    code(w, "Public articles only", J.INDEX_CHUNKS, 1)
    code(w, "Delete request", "return [{ json: { url: '__SUPABASE_URL__/rest/v1/q123_kb_chunks?id=gt.0', body: {}, timeout_ms: 20000 } }];", 2)
    http(w, "Delete old chunks", 3, cred=SUPABASE, method="DELETE")
    code(w, "Embed request", "return [$('Public articles only').first()];", 4)
    http(w, "Embed articles", 5, cred=OPENAI)
    code(w, "Chunk rows", J.INDEX_ROWS, 6)
    http(w, "Insert chunks", 7, cred=SUPABASE, headers={"Prefer": "return=minimal"})
    code(w, "Summary", J.INDEX_DONE, 8)
    respond(w, "Indexed", "={{ JSON.stringify($json) }}", 9)
    w.chain("Index request", "Public articles only", "Delete request", "Delete old chunks", "Embed request", "Embed articles",
            "Chunk rows", "Insert chunks", "Summary", "Indexed")
    return w


def build_report():
    w = WF("report", "Q123 Test: report")
    webhook(w, "Report request", "POST", "q123-report", 0)
    get_rows(w, "Log rows", "q123_log", 1)
    get_rows(w, "Agent rows", "q123_agent", 2)
    code(w, "Chunks request", "return [{ json: { url: '__SUPABASE_URL__/rest/v1/q123_kb_chunks?select=metadata', timeout_ms: 20000 } }];", 3,
         executeOnce=True)
    http(w, "Index chunks", 4, cred=SUPABASE, method="GET")
    code(w, "Collect", J.REPORT, 5, executeOnce=True)
    respond(w, "Send report", "={{ JSON.stringify($json) }}", 6)
    w.chain("Report request", "Log rows", "Agent rows", "Chunks request", "Index chunks", "Collect", "Send report")
    return w


def build_reset():
    w = WF("reset", "Q123 Test: reset")
    webhook(w, "Reset request", "POST", "q123-reset", 0)
    names = []
    for i, t in enumerate(["q123_messages", "q123_log", "q123_agent", "q123_seen"]):
        n = f"Clear {t}"
        w.add(n, "n8n-nodes-base.dataTable", 1.1, {"resource": "table", "operation": "clear", "dataTableId": table(t)},
              1 + i, executeOnce=True)
        names.append(n)
    code(w, "Label row", "return [{ json: { run_label: String(($('Reset request').first().json.body || {}).run_label || 'demo'), at: new Date().toISOString() } }];", 5)
    insert(w, "Write label", "q123_settings", 6)
    respond(w, "Done", "={{ JSON.stringify({ reset: true }) }}", 7)
    w.chain("Reset request", *names, "Label row", "Write label", "Done")
    return w


def build_setup():
    w = WF("setup", "Q123 Setup: create tables")
    webhook(w, "Run once", "POST", "q123-setup-tables", 0)
    names = []
    for i, (t, cols) in enumerate(TABLES.items()):
        n = f"Create {t}"
        w.add(n, "n8n-nodes-base.dataTable", 1.1, {
            "resource": "table", "operation": "create", "tableName": t,
            "columns": {"column": [{"name": c, "type": ty} for c, ty in cols]}}, 1 + i, executeOnce=True,
            onError="continueRegularOutput")
        names.append(n)
    respond(w, "Created", "={{ JSON.stringify({ done: true }) }}", 1 + len(TABLES))
    w.chain("Run once", *names, "Created")
    return w


# order matters for --push: a workflow's __WF:key__ references must already exist
BUILDERS = [("setup", build_setup), ("core", build_core), ("entry-test", build_test_entry), ("entry-chat", build_chat_entry),
            ("entry-whatsapp", build_whatsapp_entry), ("agent", build_agent), ("index", build_index),
            ("report", build_report), ("reset", build_reset)]


def substitute(obj, creds, wf_ids, env):
    s = json.dumps(obj)
    for k, cid in creds.items():
        s = s.replace(f"__CRED:{k}__", cid)
    for k, wid in wf_ids.items():
        s = s.replace(f"__WF:{k}__", wid)
    for ph, key in (("__SUPABASE_URL__", "Q123_SUPABASE_URL"), ("__WA_API_BASE__", "Q123_WA_API_BASE"),
                    ("__WA_VERIFY_TOKEN__", "Q123_WA_VERIFY_TOKEN")):
        s = s.replace(ph, env.get(key, "").rstrip("/"))
    if "__CRED:" in s or "__WF:" in s or "__SUPABASE_URL__" in s:
        raise SystemExit("unresolved placeholder in " + obj["name"])
    return json.loads(s)


def main():
    docs = []
    for key, fn in BUILDERS:
        d = fn().doc()
        (OUT / f"{key}.json").write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        docs.append((key, d))
    print("wrote %d workflow files" % len(docs))
    if "--push" not in sys.argv:
        return
    from n8n_api import Api, load_env
    env = load_env()
    need = ["Q123_WEBHOOK_KEY", "Q123_FORM_USER", "Q123_FORM_PASSWORD", "Q123_WA_TEST_TOKEN", "Q123_WA_TEST_SECRET",
            "Q123_WA_VERIFY_TOKEN", "Q123_SUPABASE_URL", "Q123_WA_API_BASE"]
    missing = [k for k in need if not env.get(k)]
    if missing:
        raise SystemExit("missing in .env: " + ", ".join(missing))
    api = Api()
    have = {(c.get("type"), c.get("name")): c["id"] for c in api.list_all("/credentials")}
    creds = {}
    for k, name in OWNER_CREDS.items():
        cid = have.get((k, name))
        if not cid:
            raise SystemExit(f"credential missing in n8n: {name} (type {k})")
        creds[k] = cid
    for k, (ctype, name, data) in TEST_CREDS.items():
        cid = have.get((ctype, name))
        if not cid:
            cid = api.request("POST", "/credentials", {"name": name, "type": ctype, "data": data(env)})["id"]
            print(f"created credential {name}")
        creds[k] = cid
    wf_ids = {}
    for key, d in docs:
        wid = api.push(substitute(d, creds, wf_ids, env))
        wf_ids[key] = wid
        print(f"pushed {d['name']} -> {wid}")


if __name__ == "__main__":
    main()
