"""Check that the Q123 workflows n8n runs are the committed ones (preflight item 6, eval-gate build checks).

    python tests/check_n8n_workflows.py     # exit 0 = n8n runs workflows/*.json as committed; 1 = differs

Read only: lists credentials and workflows through the n8n API and reads each Q123 workflow's published
version. The committed files get their placeholders filled the same way `workflows/build.py --push` fills
them (credential and workflow IDs from n8n, URLs from .env), then nodes, connections and settings are
compared, without IDs and positions. Prints names of differences only, never values.
Adapted from n8n-data-sync tests/n8n_match.py (same shared n8n 2.43.7).
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "workflows"))
NODE_KEYS = ("name", "type", "typeVersion", "parameters", "credentials", "onError", "retryOnFail", "maxTries",
             "waitBetweenTries", "alwaysOutputData", "executeOnce", "webhookId", "disabled")
SETTING_KEYS = ("errorWorkflow", "executionOrder")


def local_docs():
    import build
    return {key: json.loads((ROOT / "workflows" / f"{key}.json").read_text(encoding="utf-8")) for key, _ in build.BUILDERS}


def norm(doc):
    nodes = {}
    for n in doc["nodes"]:
        m = {k: n[k] for k in NODE_KEYS if k in n}
        if "credentials" in m:
            m["credentials"] = {t: c.get("id") for t, c in m["credentials"].items()}
        nodes[n["name"]] = m
    settings = {k: (doc.get("settings") or {}).get(k) for k in SETTING_KEYS}
    return {"name": doc["name"], "nodes": nodes, "connections": doc["connections"], "settings": settings}


def workflow_hash(docs):
    blob = json.dumps({k: norm(d) for k, d in sorted(docs.items())}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def compare(docs, live, creds, wf_ids, env):
    """docs: committed files by key; live: key -> workflow from GET /workflows/{id} (or None).
    Returns a list of differences; empty = n8n runs exactly the committed workflows."""
    import build
    problems = []
    for key, d in docs.items():
        w = live.get(key)
        if not w:
            problems.append(f"{d['name']}: not in n8n")
            continue
        av = w.get("activeVersion") or {}
        if not w.get("active") or not av or w.get("activeVersionId") != w.get("versionId"):
            problems.append(f"{d['name']}: not published, or the draft differs from the published version")
            continue
        try:
            want = norm(build.substitute(d, creds, wf_ids, env))
        except SystemExit:
            problems.append(f"{d['name']}: a workflow it calls is not in n8n")
            continue
        got = norm({"name": w["name"], "nodes": av.get("nodes", []), "connections": av.get("connections", {}),
                    "settings": w.get("settings") or {}})
        for n, m in got["nodes"].items():
            if "webhookId" not in want["nodes"].get(n, {}):
                m.pop("webhookId", None)  # n8n gives some nodes their own webhook ID on save
        for part in ("connections", "settings"):
            if got[part] != want[part]:
                problems.append(f"{d['name']}: {part} differ")
        for n in sorted(set(got["nodes"]) | set(want["nodes"])):
            if got["nodes"].get(n) != want["nodes"].get(n):
                problems.append(f"{d['name']}: node '{n}' differs")
    return problems


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    import build
    from n8n_api import Api, load_env
    env, api, docs = load_env(), Api(), local_docs()
    have = {(c.get("type"), c.get("name")): c["id"] for c in api.list_all("/credentials")}
    creds = {k: have.get((k, name), "missing") for k, name in build.OWNER_CREDS.items()}
    creds.update({k: have.get((ctype, name), "missing") for k, (ctype, name, _) in build.TEST_CREDS.items()})
    live, wf_ids = {}, {}
    for key, d in docs.items():
        w = api.workflow_by_name(d["name"])
        if w:
            wf_ids[key] = w["id"]
            live[key] = api.request("GET", f"/workflows/{w['id']}")
    problems = [f"credential missing in n8n: {k}" for k, v in creds.items() if v == "missing"]
    problems += compare(docs, live, creds, wf_ids, env)
    print(f"committed workflow hash {workflow_hash(docs)}")
    for p in problems:
        print("DIFF " + p)
    print("n8n runs the committed workflows" if not problems else f"{len(problems)} differences")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
