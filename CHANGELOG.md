# Changelog

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

Known limits: not tested on macOS. On Windows, the tests and the Claude Code plugin install were checked, `install.py` was not. Not tested inside ChatGPT, Codex, Cursor, Gemini CLI or the Claude app's upload screen, or in a full Claude Code session. HTTP MCP supports a bearer token, not OAuth.
