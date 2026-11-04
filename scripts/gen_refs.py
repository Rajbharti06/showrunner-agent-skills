"""Generate skill reference files from the engine data so they cannot drift from it.

    python scripts/gen_refs.py           write the files
    python scripts/gen_refs.py --check   exit 1 if any generated file is out of date (used in CI)
"""
import glob
import json
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "engine"))
os.environ["SHOWRUNNER_NO_PACKS"] = "1"  # generated files describe the free data only, never a local pack
CHECK = "--check" in sys.argv
STALE = []
DATA = ROOT + "/engine/showrunner/data"
SK = ROOT + "/skills"

EM = chr(0x2014)


def clean(s):
    return str(s).replace(EM, "U+2014")


def write(rel, text, base=None):
    path = os.path.join(base or SK, rel)
    text = text.rstrip() + "\n"
    if CHECK:
        try:
            with open(path, encoding="utf-8", newline="") as fh:
                same = fh.read() == text
        except OSError:
            same = False
        if not same:
            STALE.append(rel)
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


facts = json.load(open(DATA + "/facts.json", encoding="utf-8"))
FACTS = facts["facts"]
ASOF = facts["as_of"]
fit = json.load(open(DATA + "/fit.json", encoding="utf-8"))
slop = json.load(open(DATA + "/slop.json", encoding="utf-8"))

GEN = "_Generated from the Showrunner data files by `scripts/gen_refs.py`. Do not edit by hand. Fix the data and regenerate._"


def src(f):
    s = f.get("source") or ""
    if f.get("url"):
        return "[%s](%s)" % (s or "source", f["url"])
    return s or "no link yet"


def fact_table(rows):
    out = ["| Id | Claim | Status | Confidence | Source |", "|---|---|---|---|---|"]
    for f in rows:
        out.append("| `%s` | %s | %s | %s | %s |" % (f["id"], f["claim"].replace("|", "/"), f["status"], f["confidence"], src(f)))
    return "\n".join(out)


# ---------------------------------------------------------------- slop list
rep = slop["replace"]
lines = ["# Stock phrases and what the humanizer does with them", "", GEN, "",
         "This is a style aid. It is **not** a list of what any AI detector looks for, and removing these phrases does not make text pass a detector. They are simply phrases readers have seen too many times.", "",
         "## Replaced (%d)" % len(rep), "", "| Phrase | Becomes |", "|---|---|"]
for k, v in sorted(rep.items()):
    lines.append("| %s | %s |" % (clean(k), clean(v)))
lines += ["", "## Cut entirely (%d)" % len(slop["delete"]), ""]
lines += ["- %s" % clean(x) for x in slop["delete"]]
lines += ["", "## Flagged, not changed (%d)" % len(slop["flag"]), "",
          "These are sometimes fine. They are listed so the writer decides.", ""]
lines += ["- %s" % clean(x) for x in slop["flag"]]
lines += ["", "## Habits a script cannot fix (%d)" % len(slop["tells"]), "", "| Id | What it means |", "|---|---|"]
for t in slop["tells"]:
    lines.append("| `%s` | %s |" % (t["id"], clean(t["msg"])))
lines += ["", "## Invisible characters removed (%d)" % len(slop["invisible"]), "", "| Code point | Name |", "|---|---|"]
for k, v in slop["invisible"].items():
    lines.append("| U+%s | %s |" % (k, v))
lines += ["", "The em dash (U+2014) and curly quotes are handled separately by the `emdash` and `keep_quotes` options."]
write("sr-humanize/references/slop-list.md", "\n".join(lines))

# ------------------------------------------------------- policy checklist
pol = [f for f in FACTS if f["topic"] == "policy"]
cl = ["# Policy checklist", "", GEN, "",
      "Not legal advice. Answer each row PASS, FIX or ASK. A row marked ASK means the person has to tell you, or check the live app.", "",
      "| # | Question | If yes | Facts |", "|---|---|---|---|",
      "| 1 | Is there payment, free product, a commission, an affiliate link or a relationship with the company? | Disclose clearly, in words and with the platform label if there is one | `general.ftc_disclosure`, `general.asci_disclosure`, `general.eu_hidden_ads`, `instagram.paid_partnership` |",
      "| 2 | Does the disclosure sit where it cannot be missed (first line, spoken at the start, on screen) and not only among hashtags? | If not, move it | same |",
      "| 3 | Is there realistic AI-generated or AI-altered video, audio, voice or faces? | Use the platform setting or label | `youtube.ai_disclosure`, `tiktok.ai_label` |",
      "| 4 | Is any material reposted from someone else with nothing added? | Add real commentary or analysis, or credit and ask permission, or do not post | `general.originality_trend`, `instagram.originality.2026_04`, `youtube.originality.2026_10`, `facebook.original.2026_04` |",
      "| 5 | Is there music, footage, images or text you do not own or have a licence for? | Use the platform's licensed library or your own media | no verified fact in the database |",
      "| 6 | Does it promise or imply a result (money, health, rank, followers)? | Replace with what happened to you, with numbers, and say it was one case | no verified fact in the database |",
      "| 7 | Does it include a testimonial or review? | Real, current, with permission. Never invent one | no verified fact in the database |",
      "| 8 | Does it show an identifiable person or a child? | Get permission. Take extra care with children | no verified fact in the database |",
      "| 9 | Does the audience or the person live somewhere with extra rules? | Check local rules, or ask a professional | `general.asci_disclosure`, `general.eu_hidden_ads` |",
      "", "## Policy facts in the database (as of %s)" % ASOF, "", fact_table(pol),
      "", "Rows marked \"no verified fact in the database\" are good fact PRs. If you have a primary source, see `CONTRIBUTING.md`."]
write("sr-policy-check/references/checklist.md", "\n".join(cl))

# ------------------------------------------------------- platform files
LABEL = {p: v["label"] for p, v in fit["platforms"].items()}
CT = {"short_video": "Short video", "long_video": "Long video", "carousel": "Carousel or document", "text": "Text", "live": "Live"}
ORDER = ["limits", "formats", "signals", "policy", "features", "tools", "context", "distribution", "interop"]


def platform_section(pid):
    p = fit["platforms"][pid]
    rows = [f for f in FACTS if f["platform"] == pid]
    rows.sort(key=lambda f: (ORDER.index(f["topic"]) if f["topic"] in ORDER else 99, f["id"]))
    o = ["## %s" % p["label"], "",
         "**How people find content here (maintainer summary):** %s." % p["discovery"].rstrip("."),
         "",
         "**Maintainer's view (an opinion, not a fact):** %s" % p["note"], "",
         "**Format fit, maintainer priors from 1 to 5 (opinions you can edit in `fit.json`):**", "",
         "| Format | Fit |", "|---|---|"]
    for k, v in p["content"].items():
        o.append("| %s | %s |" % (CT.get(k, k), v))
    o += ["", "**What to measure:**", ""]
    for m in fit["measure"].get(pid, []):
        o.append("- %s" % m)
    o += ["", "**Facts in the database (as of %s):**" % ASOF, ""]
    o.append(fact_table(rows) if rows else "No facts recorded yet. This is a good place for a fact PR.")
    return "\n".join(o)


def platform_file(pids, title):
    body = ["# %s" % title, "", GEN, "",
            "Statuses: official, reported, inferred, study. Confidence: high, medium, low. Platforms change often, so anything old should be checked in the live app (`facts_stale`).", ""]
    body.append("\n\n".join(platform_section(p) for p in pids))
    body += ["", "## What nobody outside the company knows", "",
             "The exact ranking weights. Where a platform has published a list of signals but not weights, the table above says so. Treat any advice that quotes exact percentages as a guess unless it links to a primary source."]
    return "\n".join(body)


for pid, name in (("youtube", "YouTube"), ("instagram", "Instagram"), ("tiktok", "TikTok"), ("facebook", "Facebook"), ("linkedin", "LinkedIn")):
    write("sr-platform-guide/references/%s.md" % pid, platform_file([pid], name))
write("sr-platform-guide/references/x-threads.md", platform_file(["x", "threads"], "X and Threads"))

# --------------------------------------------------------- metrics by platform
sig = [f for f in FACTS if f["topic"] in ("signals",)]
m = ["# Metrics by platform", "", GEN, "",
     "Use the number that matches the goal. Views alone rarely do. Compare each post with the same account's median, not with other accounts (`sr-audit`).", ""]
for pid in fit["platforms"]:
    m.append("## %s" % LABEL[pid])
    m.append("")
    for x in fit["measure"].get(pid, []):
        m.append("- %s" % x)
    rows = [f for f in sig if f["platform"] == pid]
    if rows:
        m += ["", "Signals the platform or reports describe, with status:", ""]
        for f in rows:
            m.append("- `%s` (%s, %s confidence): %s" % (f["id"], f["status"], f["confidence"], f["claim"]))
    m.append("")
m += ["## Reading them", "",
      "- A rate (per view, per reach, per 1,000 views) beats a count.",
      "- A share of viewers who stayed beats the average view time on its own, because a few long watchers can lift an average.",
      "- Read at least ten posts before calling a pattern, and four per variant before calling a test (`sr-growth-loop`).",
      "- Write down what each metric means before you read it. \"Engaged view\" and \"chose to view\" are not the same thing."]
write("sr-audit/references/metrics-by-platform.md", "\n".join(m))

# ------------------------------------------------------------ playbook catalogue
pbs = [json.load(open(f, encoding="utf-8")) for f in sorted(glob.glob(DATA + "/playbooks/*.json"))]
pc = ["# Playbook catalogue", "", GEN, "",
      "Start one with `playbook_start` (CLI `python scripts/sr.py playbook start <id>`). Gates: `approve` means show the work and wait for a yes. `human` means the person does it outside the chat. `data` means the person brings numbers. `auto` means the assistant can do it.", ""]
for pb in pbs:
    pc += ["## %s (`%s`)" % (pb["title"], pb["id"]), "", "%s" % pb["summary"], "",
           "Duration: %s. Use when: %s" % (pb["duration"], pb["when"]), "",
           "| # | Step | Skill | Gate | Produces |", "|---|---|---|---|---|"]
    for i, s in enumerate(pb["steps"], 1):
        pc.append("| %d | %s | `%s` | %s | %s |" % (i, s["title"], s["skill"], s["gate"], s.get("produces", "")))
    pc.append("")
write("showrunner/references/playbooks.md", "\n".join(pc))

# ------------------------------------------------------------- hook shapes
hk = json.load(open(DATA + "/hooks.json", encoding="utf-8"))["formulas"]
h = ["# Hook shapes", "", GEN, "",
     "%d structures the scorer recognises. Fill the braces with true details from the creator's own experience. Never invent the number or the story." % len(hk), "",
     "| Shape | Template | Good for | Ruined by |", "|---|---|---|---|"]
for x in hk:
    h.append("| %s | `%s` | %s | %s |" % (x["name"], x["template"], x["purpose"].replace("|", "/"), x["ruins"].replace("|", "/")))
h += ["", "## Worked examples", "", "These examples are invented to show the shape. Do not copy their numbers or stories.", ""]
for x in hk:
    h.append("- **%s:** %s" % (x["name"], x["example"]))
write("sr-hook/references/hook-shapes.md", "\n".join(h))

# ------------------------------------------------- skills catalogue and MCP tool list
import re  # noqa: E402
from showrunner import tools as T  # noqa: E402

GROUPS = [
    ("Orchestrate", ["showrunner", "sr-intake", "sr-strategy", "sr-voice"]),
    ("Research", ["sr-research", "sr-outliers", "sr-ideas", "sr-profile-audit"]),
    ("Make", ["sr-hook", "sr-script", "sr-title-thumbnail", "sr-caption", "sr-carousel", "sr-text-post", "sr-edit-plan", "sr-repurpose", "sr-humanize"]),
    ("Check and prepare", ["sr-policy-check", "sr-seo", "sr-calendar", "sr-platform-guide"]),
    ("Learn", ["sr-engage", "sr-audit", "sr-growth-loop"]),
]
tool_names = [t.name for t in T.TOOLS]
cat = ["# The 24 skills", "", GEN, "",
       "Every skill works without code, by following the method written in it. Where there is a tool, the skill names it.", ""]
seen = set()
for title, names in GROUPS:
    cat += ["## %s" % title, "", "| Skill | What it does | Tools |", "|---|---|---|"]
    for n in names:
        seen.add(n)
        body = open(os.path.join(SK, n, "SKILL.md"), encoding="utf-8").read()
        desc = re.search(r"^description: (.*)$", body, re.M).group(1)
        first = desc.split(". ")[0].rstrip(".") + "."
        used = [t for t in tool_names if re.search(r"\b%s\b" % t, body.split("---", 2)[2])]
        cat.append("| [`%s`](../skills/%s/SKILL.md) | %s | %s |" % (n, n, first.replace("|", "/"), ", ".join("`%s`" % u for u in used) or "none, method only"))
    cat.append("")
missing = sorted(set(os.listdir(SK)) - seen)
if missing:
    sys.stderr.write("Skills not in a group in gen_refs.py: %s\n" % ", ".join(missing))
    sys.exit(2)
write("docs/skills.md", "\n".join(cat), base=ROOT)

mt = ["# MCP tools", "", GEN, "",
      "%d tools. Over stdio all are available. Over HTTP the %d marked read-only are available by default; tools that save to the local folder need `--stateful` and a single trusted user." % (
          len(T.TOOLS), sum(1 for t in T.TOOLS if not t.stateful)), "",
      "| Tool | CLI command | Saves to disk | What it does |", "|---|---|---|---|"]
for t in T.TOOLS:
    mt.append("| `%s` | `showrunner %s` | %s | %s |" % (t.name, t.cli, "yes" if t.stateful else "no", t.summary.replace("|", "/")))
write("mcp/tools.md", "\n".join(mt), base=ROOT)

if CHECK:
    if STALE:
        sys.stderr.write("Out of date, run `python scripts/gen_refs.py`:\n  " + "\n  ".join(STALE) + "\n")
        sys.exit(1)
    print("references up to date")
else:
    print("references written")

