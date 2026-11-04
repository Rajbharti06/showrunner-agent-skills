# How Showrunner is put together

Short version: the skills are instructions, the engine is the arithmetic, and the facts file is the only place a platform rule is allowed to live. The assistant does the thinking and the talking. The engine does the counting. Neither pretends to be the other.

## The three layers

```
 you
  |
  v
 skills/            24 folders of instructions (SKILL.md + references/).
  |                 They tell the assistant what to ask, which tool to run, how to read the result.
  v
 engine/showrunner  One Python package, standard library only.
  |                 34 tools in one registry. Same tools reached two ways:
  |                   - CLI:  python skills/showrunner/scripts/sr.py <command>  (or `showrunner <command>` after pip install .)
  |                   - MCP:  showrunner-mcp (stdio or HTTP)
  v
 data/              facts.json, hooks.json, slop.json, weights.json, playbooks/*.json
 ~/.showrunner      your profile, experiments, playbook runs, calibrated weights
```

A skill never contains a platform number. If it needs one, it tells the assistant to run `facts_search` and quote the answer along with its status and date. That is why the facts live in one file and why CI can check them.

## Why a registry

Every tool is declared once in `tools.py` with a name, a description, typed parameters and a function. The CLI parser, the MCP tool list, `docs/skills.md` and `mcp/tools.md` are all built from that single declaration. A tool cannot exist in one surface and be missing from another, and the validator fails the build if a skill mentions a tool or flag that is not in the registry.

Tools return one shape: `{"ok": bool, "text": str, "data": {...}}`. The text is for people, the data is for the assistant. 25 of the 34 tools are read-only. The other 9 write to `~/.showrunner` (profile, experiments, playbook runs, weights) and are switched off in the HTTP server unless you start it with `--stateful`.

## The engine, module by module

| Module | What it does |
|---|---|
| intake | Turns what you want, who it is for, where it goes and how many hours you have into a platform plan with a hub, spokes and a "later" list |
| planner | Capacity-aware calendar. Effort per format, a batching discount, time reserved for replying to comments |
| playbooks | The orchestration layer. Multi-step sequences stored as data, with run state saved between sessions |
| facts | Platform rules with status, confidence, source link and an as-of date. Flags anything older than 90 days |
| hooks | Scores an opening line against 32 hook shapes and a set of dealbreakers |
| titles | Scores YouTube-style titles and pairs them with a thumbnail text |
| captions | Lints post copy and shows what the feed will cut off |
| beats | Splits a script into timed beats and flags retention problems before you shoot |
| srt | Reads SRT and VTT, finds dead air and fillers, re-chunks for vertical video |
| clips | Finds self-contained clips in a long transcript |
| retention | Reads a retention curve and names its shape |
| outliers | Ranks a creator's posts against their own median |
| ideas | Scores and de-duplicates ideas, builds a pillar-by-angle matrix |
| humanize | A style editor for stock phrases and rhythm. It is not a detector bypass |
| experiments | Logs a test and checks it with a rank-sum permutation test |
| calibrate | Checks whether the hook score separates your winners from your misses, and can write your own weights |
| store | Reads and writes your state |
| render | Plain-text output for tools that do not format themselves |
| mcp_server | JSON-RPC over stdio or HTTP, plus the prompts start, weekly and monthly |

## How a request flows

You say "I want to start posting about woodworking". The `showrunner` skill loads, finds no saved profile, and hands over to `sr-intake`. That skill asks the four questions, calls `intake_plan`, and shows a plan with a clear hub platform and short list of spokes. If you have little time it says which platforms wait. You approve, and `profile_save` stores the answers. From then on `sr-strategy`, `sr-ideas`, `sr-script` and the rest read the profile instead of asking again.

Playbooks sit on top. `playbook_start zero-to-first-1000` creates a run with ordered steps, each pointing at a skill. `playbook_next` says what is next. The run survives between sessions because it is saved to disk, not to chat history.

## The honesty layer

This is the part that most repos of this kind skip, so it has its own file: [honesty.md](honesty.md). In short:

1. Scorers are heuristics and say so. Run `calibrate` on your own posts to see whether they work for you. It needs 8 posts to run and 30 before it will write weights.
2. Facts carry their origin. Official means the platform says it. Reported means someone else says the platform said it. Study and inferred are labelled. Reported and study facts must have a link or the test suite fails.
3. Experiments say "not enough posts" below 4 per variant instead of declaring a winner.
4. Nothing posts. There is no login, no token handling and no scheduler call anywhere in the engine.

## Adding things

A new fact is one entry in `engine/showrunner/data/facts.json` with a status, a link and an `as_of` date, then `python scripts/gen_refs.py` to regenerate the platform guides. A new tool is one entry in `tools.py`. A new skill is a folder with a `SKILL.md`; run `python scripts/sync_shims.py` to copy the runner into it and `python scripts/validate_skills.py` to check it. CONTRIBUTING.md has the full list.

## Data packs

A data pack extends the shipped data without forking the engine. It is a folder with a `pack.json` (`id`, `name`, `version`) and any of the data files, for example `hooks.json` or `slop.json`, plus an optional `playbooks/` folder. The engine looks for packs in `engine/showrunner/data/packs/`, in `~/.showrunner/packs` (or `SHOWRUNNER_HOME/packs`), and in the folders listed in `SHOWRUNNER_PACKS`. `doctor` lists the packs in use.

`hooks.json` may also carry a `lexicon` (`second_person`, `first_person`, `audience`, `stakes`, `filler_open`, `curiosity_rx`) that adds words to the hook scorer's built-in lists, so a language pack can score hooks in that language fairly.

Packs only add. Lists are extended and new keys are added, but a pack cannot change a shipped value or replace a shipped playbook. Packs are JSON, never code. A pack's patterns run like the shipped ones, so only install packs you trust.

`SHOWRUNNER_NO_PACKS=1` turns packs off. The generators, the validator and the tests set it, so a pack installed on a maintainer's machine never ends up in generated files. `install.py` and `build_dist.py` leave `data/packs/` out when they copy the engine, and `.gitignore` keeps it out of the repo.

## What is deliberately not here

No platform API clients, no scraping, no scheduling or auto-posting, no stored credentials, and no outbound network calls from the engine. That keeps the install a copy-paste and keeps accounts safe. If you want posting, pair this with a scheduler you trust and let Showrunner decide what to post and when.
