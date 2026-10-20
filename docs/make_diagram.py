"""Draw docs/architecture.png (what happens to one customer message). Run: python docs/make_diagram.py"""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

INK, MUTED = "#1f2937", "#6b7280"
FILL = {"step": "#eef2ff", "ai": "#fef3c7", "check": "#ede9fe", "person": "#dcfce7", "stop": "#f3f4f6"}

BOXES = {
    "msg": (0.9, 6.0, "Customer message\n(web chat or WhatsApp)", "step"),
    "pre": (3.6, 6.0, "Code pre-check:\nasks for a person?\nsafety words?", "check"),
    "search": (6.3, 6.0, "Find the 8 closest\nhelp articles\n(Supabase)", "step"),
    "ai": (9.0, 6.0, "Claude writes the reply,\npicks a route and\nnames its articles", "ai"),
    "chk": (11.7, 6.0, "Code checks the reply:\nevery number and link\nin the cited article?", "check"),
    "send": (14.4, 6.0, "Send the reply\n(\"I don't know\" adds\nan offer of a colleague)", "step"),
    "fake": (0.9, 3.6, "WhatsApp request\nwith a bad signature:\nrefused, nothing sent", "stop"),
    "down": (6.3, 3.6, "Service down after\none retry: fallback\nmessage + Slack alert", "stop"),
    "hand": (9.0, 3.6, "Hand off in Slack:\nfull conversation,\nreason, reply form", "person"),
    "reply": (11.7, 3.6, "Person replies through\nthe form; bot silent\nuntil \"close\"", "person"),
}
ARROWS = [
    ("msg", "pre", ""), ("pre", "search", "no"), ("search", "ai", ""), ("ai", "chk", "answer"),
    ("chk", "send", "pass"), ("msg", "fake", "bad signature"), ("search", "down", "fails"),
    ("pre", "hand", "yes"), ("ai", "hand", "hand off"), ("chk", "hand", "check fails"), ("hand", "reply", ""),
]
W, H = 2.25, 1.15

fig, ax = plt.subplots(figsize=(16, 6.6), dpi=150)
ax.set_xlim(-0.6, 15.8)
ax.set_ylim(1.4, 7.2)
ax.axis("off")
fig.patch.set_facecolor("white")

for key, (x, y, text, kind) in BOXES.items():
    ax.add_patch(FancyBboxPatch((x - W / 2, y - H / 2), W, H, boxstyle="round,pad=0.02,rounding_size=0.12",
                                fc=FILL[kind], ec=INK, lw=1.2))
    ax.text(x, y, text, ha="center", va="center", fontsize=9.3, color=INK)

# Diagonal arrows get explicit start/end points so they pass between the boxes.
ANCHORS = {
    ("pre", "hand"): (lambda a, b: ((a[0] + 0.5, a[1] - H / 2), (b[0] - 0.6, b[1] + H / 2))),
    ("chk", "hand"): (lambda a, b: ((a[0] - 0.5, a[1] - H / 2), (b[0] + 0.6, b[1] + H / 2))),
}


def edge(a, b):
    if (a, b) in ANCHORS:
        return ANCHORS[(a, b)](BOXES[a], BOXES[b])
    (xa, ya, *_), (xb, yb, *_) = BOXES[a], BOXES[b]
    if abs(ya - yb) < 0.01:
        sx = 1 if xb > xa else -1
        return (xa + sx * W / 2, ya), (xb - sx * W / 2, yb)
    sy = 1 if yb > ya else -1
    return (xa, ya + sy * H / 2), (xb, yb - sy * H / 2)


for a, b, label in ARROWS:
    p, q = edge(a, b)
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=12, color=INK, lw=1.1))
    if label:
        flat = abs(p[1] - q[1]) < 0.01
        t = {("pre", "hand"): 0.25, ("search", "down"): 0.78}.get((a, b), 0.5)  # keep labels off the crossing
        ax.text(p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1]) + (0.2 if flat else 0), label, ha="center", va="center",
                fontsize=8.5, color=MUTED, style="italic", bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none"))

ax.text(-0.5, 7.0, "n8n AI Support Bot: what happens to one customer message", fontsize=13, weight="bold", color=INK)
legend = [("step", "automatic step"), ("ai", "AI step"), ("check", "code check (no AI)"),
          ("person", "a person"), ("stop", "stopped / fallback")]
for i, (kind, label) in enumerate(legend):
    ax.add_patch(FancyBboxPatch((-0.5 + i * 2.4, 1.55), 0.35, 0.3, boxstyle="round,pad=0.01", fc=FILL[kind], ec=INK, lw=0.8))
    ax.text(-0.05 + i * 2.4, 1.7, label, va="center", fontsize=8.5, color=INK)
ax.text(13.3, 2.55, "Every message is logged:\nroute, articles, check results,\nmodel, tokens, cost, seconds.",
        fontsize=8.5, color=MUTED, va="center")

out = Path(__file__).with_name("architecture.png")
fig.savefig(out, bbox_inches="tight")
print("wrote", out)
