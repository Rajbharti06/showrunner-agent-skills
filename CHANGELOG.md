# Changelog

## 0.1.2 (2026-11-04)

- **Data packs.** A folder with a `pack.json` and any data files (`hooks.json`, `slop.json`, ...) plus an optional `playbooks/` folder now extends the shipped data without forking the engine. Packs are found in `data/packs/`, in `~/.showrunner/packs` and via `SHOWRUNNER_PACKS`, and `doctor` lists them. Packs only add: shipped values and playbooks stay as they are. See "Data packs" in docs/architecture.md.
- `hooks.json` may carry a `lexicon` that adds words to the hook scorer's lists (stakes, audience, second and first person, filler, curiosity), so a language pack can score hooks in that language fairly. Without a pack, every score is unchanged.
- `SHOWRUNNER_NO_PACKS=1` turns packs off. The generators, the validator and the tests set it, and `install.py`, `build_dist.py` and `.gitignore` keep local packs out of the free files.
- 85 tests.

## 0.1.1 (2026-11-03)

Found by running the plugin in a live Claude Code session on Windows. Each fix has a test.

- Boolean flags take a word too: `--on-camera no`, `--on-camera=yes`, and `--no-on-camera`. Before, `--on-camera no` was an error, and leaving the flag out lost the faceless advice.
- `profile save` takes the same flags as `intake`, and a one-item list for `content_type`.
- `playbook show` lists step ids, and each step says how to skip it.
- The conductor and intake skills: at most two questions per message, run `scripts/sr.py` by its full path instead of changing into the skill folder, how to skip a step and what it costs, and ask which language the content is in before drafting.
- `install.py` quotes the path in its closing hint (user folders often have spaces) and names a skill that was installed.
- docs/honesty.md: the hook scorer's dealbreaker patterns are English only.

## 0.1.0 (2026-11-02)

First public version.

- 24 Agent Skills: a conductor, intake, strategy, voice, profile audit, research, outliers, ideas, hooks, scripts, titles and thumbnails, captions, carousels, text posts, edit plans, repurposing, humanizing, policy check, search, calendar, platform guide, engagement, audit and growth loop.
- Zero-dependency Python engine with 34 tools shared by a CLI and an MCP server (stdio, plus optional read-only streamable HTTP).
- 7 playbooks with approval gates, and run state kept in `~/.showrunner`.
- 43 platform facts, each with a status, confidence and date. `calibrate` tests the scorers against your own posts. Experiments use a rank-sum permutation test.
- Planner that sizes the week to real hours, exports Markdown, CSV, `.ics` and JSON.
- `install.py` for Claude, Cursor, Gemini CLI and the shared `.agents/skills` folder. `build_dist.py` for upload-ready zips with fixed timestamps, so the same inputs give the same zips on the same Python.
- Claude Code plugin manifest and marketplace file.
- Custom GPT instructions and knowledge list.
- 76 tests, a skill validator that checks every tool, flag and fact id the skills mention, and a prose linter.

Known limits: the tests and repo checks pass in CI on Linux, Windows and macOS. The Claude Code plugin install was checked on Windows only, and `install.py` on Linux only. Not tested inside ChatGPT, Codex, Cursor, Gemini CLI or the Claude app's upload screen, or in a full Claude Code session. HTTP MCP supports a bearer token, not OAuth.
