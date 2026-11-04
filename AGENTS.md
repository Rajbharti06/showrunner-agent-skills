# Notes for AI coding agents working on this repository

Read this before changing anything. Humans can read it too.

## What this repo is

Agent Skills (`skills/*/SKILL.md`) plus a zero-dependency Python 3.9+ engine (`engine/showrunner`) that the skills call through `scripts/sr.py`. The engine has one tool registry (`engine/showrunner/tools.py`) that feeds both the CLI (`cli.py`) and the MCP server (`mcp_server.py`).

## Commands

```
python -m unittest discover -s tests      all tests
python scripts/validate_skills.py         spec check + every tool, flag, fact id and skill name in SKILL.md is real
python scripts/lint_prose.py              fails on em dashes outside the allowlist
python scripts/sync_shims.py [--check]    copies scripts/sr_shim.py into every skill
python scripts/gen_refs.py [--check]      regenerates skill references, docs/skills.md, mcp/tools.md
python scripts/build_dist.py              zips into dist/
```

Run all five checks before you finish. They are what CI runs.

## Do not edit by hand

Files that start with "Generated from the Showrunner data files" are written by `scripts/gen_refs.py`. Change the data (`engine/showrunner/data/*.json`) or the generator. `skills/*/scripts/sr.py` are copies of `scripts/sr_shim.py`.

## Rules that matter

1. **Never quote a platform fact from memory.** Facts live in `data/facts.json` with a status, confidence, source and date. If you add one, it needs a source URL unless it is `official`, and you may not mark something `official` unless the platform itself states it.
2. **Scores are heuristics.** Do not describe a scorer as accurate, proven or predictive. Describe what it checks.
3. **Skills must not promise what the engine cannot do.** `validate_skills.py` enforces tool names, parameters, CLI examples and fact ids. Keep it passing.
4. **Nothing posts.** No skill, tool or MCP method may publish, schedule or send on the user's behalf.
5. **No network calls in the engine. No dependencies.**
6. **Stateful tools** (anything writing to `~/.showrunner`) must be flagged `stateful`, so the HTTP server hides them by default.
7. **Writing style.** No em dashes. Plain, specific, human sentences. No hype. No claims that something works somewhere it was not tested. The README's "tested and not tested" section must stay true.

## Where things are

| To change | Edit |
|---|---|
| A platform fact | `engine/showrunner/data/facts.json`, then `gen_refs.py` |
| Platform fit priors | `engine/showrunner/data/fit.json` |
| Hook shapes | `engine/showrunner/data/hooks.json` |
| Stock phrases the humanizer cuts | `engine/showrunner/data/slop.json` |
| Extra data without forking the engine | A data pack, see "Data packs" in `docs/architecture.md`. Never commit one to this repo |
| A playbook | `engine/showrunner/data/playbooks/<id>.json` (steps use skill names that must exist) |
| A tool | `engine/showrunner/tools.py` (add the `Tool(...)` entry; CLI and MCP pick it up) |
| A skill | `skills/<name>/SKILL.md` |

## Tests

`tests/test_engine.py` and `tests/test_mcp.py`, standard `unittest`. Tests set `SHOWRUNNER_HOME` to a temp folder so they never touch a real profile. Add a test for every bug you fix.
