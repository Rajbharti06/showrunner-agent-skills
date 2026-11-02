# Showrunner

**Tell your AI what you want to make, who it is for and where it will go. It asks the right questions first, picks one main platform that fits your real weekly hours, writes the plan and the drafts in your voice, and then tells you honestly what worked.**

24 Agent Skills and a small Python engine for growing a channel on YouTube, Instagram, TikTok, Facebook, LinkedIn, X and Threads. Written to the open Agent Skills format that Claude, ChatGPT, Codex, Cursor and Gemini CLI load. No dependencies. MIT licensed.

![license](https://img.shields.io/badge/license-MIT-blue) ![python](https://img.shields.io/badge/python-3.9%2B-blue) ![dependencies](https://img.shields.io/badge/dependencies-none-brightgreen) ![skills](https://img.shields.io/badge/skills-24-orange) [![CI](https://github.com/Rajbharti06/showrunner-agent-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/Rajbharti06/showrunner-agent-skills/actions/workflows/ci.yml)

It writes and plans. **It never posts.** Nothing goes out until you say yes and press the button yourself.

---

## What happens when you start

You say: *I want to grow my channel.* The conductor skill asks seven questions, one or two at a time, in your own words and your own language, including Hindi, Hinglish and mixed scripts.

```
1. What do you want to make?            short video, long video, carousel, text, a mix
2. Who is it for?                       a sentence: their situation, region, what they are trying to do
3. What do you want out of it?          audience, leads, authority, income, community
4. Where do you already post, or want to?   "not sure" is fine
5. Where are you now?                   zero, under 1,000, 1,000 to 10,000, over 10,000
6. How many hours a week, honestly?     filming and editing included
7. Are you willing to be on camera?     faceless formats plan differently
```

It does not recommend a platform before you have answered. Then it recommends one **hub** where the main piece is made, one or two **spokes** that reuse it cheaply, and what to **skip for now**, sized to your hours. This is real output for a student creator with five hours a week:

```
RANKING (fit 0 to 100)
   95.3  TikTok     HUB    one of the strongest fits for your goal; built for the format you want to make
   84.0  YouTube    spoke  your audience is concentrated here; heavy for 5 hours a week
   79.0  Instagram  later  you asked for it, but 5 hours a week fits 2 platforms
   53.8  LinkedIn   skip   average fit across the board
Hub: tiktok    Spokes: youtube    Skip for now: instagram, linkedin, facebook, threads, x
Weekly load: 231 min planned of a 255 min creation budget (+45 min for replies and DMs)
  tiktok     short_video  3 per week  (~56 min each, made fresh)
  youtube    short_video  3 per week  (~21 min each, adapted from the hub piece)
```

It tells you when you asked for more than your week can hold. The ranking comes from the maintainer's priors in [`fit.json`](engine/showrunner/data/fit.json), which are opinions you can edit, and the output says so.

## Then it does the work, one gated step at a time

Seven playbooks chain the skills. Each step has a gate: **approve** (it shows you the work and waits for a yes), **human** (only you can do it, like filming or posting), **data** (you bring numbers) or **auto**.

| Playbook | Use it when | Steps |
|---|---|---|
| `zero-to-first-1000` | You are starting and want a plan you can finish. A plan, not a promise | 18 |
| `weekly-sprint` | Every week once the plan is set | 12 |
| `one-to-many` | You have a long video, talk or article and want a week of content from it | 7 |
| `youtube-video-launch` | A long video, with packaging and retention done right | 9 |
| `profile-makeover` | Your profiles do not say who you help or why to follow | 6 |
| `monthly-review` | Once a month, every month | 8 |
| `campaign-sprint` | You are launching something | 8 |

## See the tools work

These are real outputs from the example data in [`examples/`](examples) (all of it invented).

**Rank hooks.** Heuristic, and it says so:

```
1. [ 67.2 OK]  I sat in on 41 interviews. 33 candidates failed the same way in the first five minutes.
   weakest: curiosity. Hold something back. End the line on the unresolved part, not the answer.
4. [ 35.0 WEAK]  You won't believe what this interviewer told me
   DEALBREAKER: Asking for attention proves you have not earned it. Say the thing instead.
5. [ 20.2 WEAK]  Hey guys, welcome back to my channel
   DEALBREAKER: Greeting. Nobody opened the feed to be greeted.
```

**Find the clips in a long video** and get a ready-to-run ffmpeg command for each:

```
#1  0:07.5 - 0:37.2  (30s)  score 79  hook 64  self-contained 100  payoff 50
    ffmpeg -ss 00:00:07.550 -i "talk.mp4" -t 29.670 -vf "crop=ih*9/16:ih,scale=1080:1920,setsar=1" ...
```

**Check whether its own score works for you.** This is the part most tools skip:

```
check           AUC   90% interval     verdict
specificity   0.696   0.56 to 0.83      separates winners from misses on this data
total         0.610   0.45 to 0.76      indistinguishable from a coin flip here
  - One account. The result describes your audience and nobody else's.
```

On the example data the total score is a coin flip, and the tool tells you that. Every scorer here is a heuristic until this check says otherwise for your account.

## Start in five minutes

Pick your tool. You need Python 3.9 or newer only if you want the scoring tools. Every skill also works by following the method written in it.

| You use | Do this |
|---|---|
| **Claude Code** | `/plugin marketplace add Rajbharti06/showrunner-agent-skills` then `/plugin install showrunner@showrunner`. Or `git clone` this repo and run `python install.py --target claude` |
| **Claude (app or web)** | Upload the zips from [`dist/skills/`](dist) (run `python scripts/build_dist.py`, or take them from a release) in Claude's skills settings. Start with `showrunner.zip` |
| **ChatGPT** | Upload the zips as skills on a paid plan, or build a Custom GPT. Steps in [docs/chatgpt.md](docs/chatgpt.md) |
| **Codex, Cursor, Gemini CLI** | `python install.py --target agents` (the shared `~/.agents/skills` folder). Or `--target cursor` or `--target gemini`. Details below |
| **Anything that speaks MCP** | `pip install .` then `showrunner-mcp`. Config for each client in [mcp/README.md](mcp/README.md) |

Then open a new session and say: **I want to grow my channel.**

Where each agent looks for skills, as of November 2026:

| Agent | Project folder | User folder | Basis |
|---|---|---|---|
| Claude Code | `.claude/skills` | `~/.claude/skills` | Claude Code convention; Cursor also reads these |
| Cursor | `.cursor/skills`, `.agents/skills` | `~/.cursor/skills`, `~/.agents/skills` | [Cursor docs](https://cursor.com/docs/skills) |
| Gemini CLI | `.gemini/skills`, `.agents/skills` | `~/.gemini/skills`, `~/.agents/skills` | [Gemini CLI docs](https://geminicli.com/docs/cli/skills/) |
| Codex | `.agents/skills` | `~/.agents/skills` | Not confirmed against OpenAI's docs. Check them if it does not load |

`install.py` copies each skill with its own bundled copy of the engine, so each one runs alone. `python install.py --list` shows what it will install and `--only sr-hook,sr-script` installs a few.

## What is inside

| Group | Skills |
|---|---|
| **Orchestrate** | `showrunner` (the conductor), `sr-intake`, `sr-strategy`, `sr-voice` |
| **Research** | `sr-research`, `sr-outliers`, `sr-ideas`, `sr-profile-audit` |
| **Make** | `sr-hook`, `sr-script`, `sr-title-thumbnail`, `sr-caption`, `sr-carousel`, `sr-text-post`, `sr-edit-plan`, `sr-repurpose`, `sr-humanize` |
| **Check and prepare** | `sr-policy-check`, `sr-seo`, `sr-calendar`, `sr-platform-guide` |
| **Learn** | `sr-engage`, `sr-audit`, `sr-growth-loop` |

[docs/skills.md](docs/skills.md) says what each one does and which tools it uses. There are 34 tools in the engine (CLI and MCP share one registry), 32 hook shapes, 43 platform facts with statuses and dates, and 7 playbooks.

## Honest by design

Most "algorithm" advice is a guess said confidently. Showrunner is built to keep the guesses apart from the facts.

- **Every platform fact has a status** (official, reported, inferred or study), a confidence, a source note and a date, plus a link wherever one was verified. Some limits do not have a verified link yet, and `showrunner doctor` counts them. Nothing is quoted from memory. Facts older than 90 days are flagged.
- **Scores are heuristics and say so.** Hook, title and caption scores have not been validated against views. The `calibrate` tool tests them against your own posts and only saves new weights from 30 or more.
- **Tests need enough posts.** The experiment tool refuses to call a winner from fewer than four posts per variant.
- **The humanizer is a style editor, not a detector bypass.** It makes no claim about any AI detector and tells you to disclose AI use where a rule requires it.
- **It never invents your story.** Hooks and scripts use details you give it. It asks for the number, the name and the mistake.

Read [docs/honesty.md](docs/honesty.md) for exactly what is and is not validated.

## How it relates to other projects

Single-platform skill packs go deep on one platform. [Jake Schincariol's instagram-agent-skill](https://github.com/Jakeschincariol/instagram-agent-skill) is a good example, and it inspired the zero-dependency tools, the "these skills write, you post" rule and the focus on honest measurement here. Showrunner goes across platforms and adds the intake, the planner, the playbooks and the learning loop. If you only work on one platform, a dedicated pack may go deeper there.

vidIQ offers an MCP connector with keyword and competitor data, which Showrunner does not have. If you use it, connect it and the conductor can use its data (`showrunner facts --id tooling.vidiq.mcp`). Showrunner is not affiliated with vidIQ, Anthropic, OpenAI, or any platform named here. Names belong to their owners.

## What is tested, and what is not

Tested: the engine and tools on Python 3.9, 3.11, 3.12 and 3.13 on Linux, with 76 tests. The MCP server over stdio and HTTP with a protocol test suite. The ffmpeg commands against a real generated video. The calendar's `.ics` output against a calendar parser. Installing with `pip` and with `install.py`, and running a single unzipped skill with nothing else installed.

**Not tested by the maintainers:** Windows and macOS (CI runs them best effort), and loading the skills inside ChatGPT, Codex, Cursor, Gemini CLI, the Claude app upload screen or the Claude Code plugin marketplace. They were written to each tool's published format. If one does not load, open an issue with what you saw.

## Contributing

The most useful pull request is a **fact PR**: a platform rule that changed, or a new one with a primary source. See [CONTRIBUTING.md](CONTRIBUTING.md). Second most useful: run `calibrate` on your own posts and share what you learned in an issue (no raw data needed).

## Layout

```
skills/        24 skills, each a folder with SKILL.md (and references/)
engine/        the Python package: tools, planner, facts, playbooks, MCP server
examples/      invented sample data you can run every tool on
docs/          how it works, honesty notes, ChatGPT setup, launch notes for maintainers
mcp/           connect the engine as an MCP server; generated tool list
gpt/           Custom GPT instructions and knowledge file list
scripts/       validators, generators and the zip builder
tests/         76 tests
.github/       CI, issue and pull request templates
.claude-plugin/  Claude Code plugin and marketplace manifests (not tested)
```

How the pieces fit together is in [docs/architecture.md](docs/architecture.md). If you are the one publishing this repo, read [docs/launch-playbook.md](docs/launch-playbook.md) first.

## License

MIT. See [LICENSE](LICENSE).
