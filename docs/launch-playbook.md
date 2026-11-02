# Launch playbook (for the maintainer)

This file is for whoever publishes the repo. It is not for users. Delete it or keep it, but read it before you push.

One honest sentence first: no repository can promise stars. What you can control is whether the first ten people who try it have a good time, whether the README shows the thing working in under a minute, and whether you answer issues fast. Everything below is about those three things.

## Before the first push

1. **Check the name.** "Showrunner" is a working title. At least one unrelated company in AI video uses it, and the word is common in film and TV. Search GitHub, npm, PyPI and the trademark database for your country before you put it on a logo or a domain. If you rename, search the repo for `showrunner` and `Showrunner` and for the repo URL in `README.md`, `pyproject.toml`, `.claude-plugin/plugin.json` and `.github/`. The Python package name in `pyproject.toml` is the one that matters for `pip`.
2. **Fix the URLs.** Everything assumes `github.com/Rajbharti06/showrunner-agent-skills`. If your repo has another name, change it in the files above and in the README CI badge.
3. **Run the checks once on a clean clone.** The five commands in CONTRIBUTING.md, then `python scripts/build_dist.py`.
4. **Read the README as a stranger.** The first screen should answer three questions: what is it, why is it not the same as the fifteen other skill repos, and how do I try it in one minute. If you have to scroll for the third, move it up.

## Repository settings

Description (about 120 characters is plenty): *24 Agent Skills that ask what you want to make, for whom and where, then plan, write and check content across YouTube, Instagram, TikTok, LinkedIn and more. Never posts.*

Topics to add: `agent-skills`, `claude-code`, `claude-skills`, `chatgpt`, `codex`, `cursor`, `gemini-cli`, `mcp`, `content-creation`, `youtube`, `instagram`, `tiktok`, `social-media`, `creator-tools`.

Social preview: a 1280 by 640 image in Settings. Plain text on a plain background beats a busy graphic. Put the one-line pitch on it. There is one ready at [`docs/social-preview.png`](social-preview.png). GitHub has no API for this, so upload it by hand under Settings, General, Social preview.

Turn on Discussions so questions have somewhere to go that is not Issues. Pin one issue called "Good first fact checks" that lists the 15 facts without a verified link (`showrunner doctor` prints the count). It gives newcomers an easy first pull request, and that is how a small repo gets its first contributors.

## The demo

People decide in about ten seconds. A short screen recording of the intake beats any amount of README. Record it like this: open Claude Code or your assistant in an empty folder, say "I want to start posting about woodworking, I have four hours a week", let it ask the questions, show the plan it produces with one hub and the "later" list. Under 45 seconds, no music, captions on. Export as a GIF or MP4 and put it at the top of the README.

A second, even shorter clip is worth making: run `calibrate` on the example data and let it say that the hook score mostly cannot tell winners from misses. That is the honest part of this project, and almost nobody else shows it.

## Where to post

Pick two places, not ten. Read each place's rules on self-promotion first, because getting removed is worse than not posting.

Hacker News: a Show HN post with a plain title (what it is, not how great it is) and a first comment from you that says why you built it and what does not work yet. Read the Show HN guidelines before you post. Do not ask friends to upvote, since the site watches for that.

Reddit: communities where people use Claude, ChatGPT, Cursor or Codex, and communities for creators on YouTube or Instagram. The two audiences want different posts. Creators want the plan and the drafts; builders want the engine and the honesty layer. Lead with a result, not with a link.

Awesome lists: search GitHub for "awesome" lists of agent skills and of Claude Code resources, read the contributing file of each, and open a pull request that follows its format exactly. Do not name a list in your pitch that you have not read.

Your own accounts: use the thing yourself first. A thread or video that shows the repo making a real plan for a real channel is worth more than an announcement.

## Release checklist

1. Update `CHANGELOG.md` and the version in `pyproject.toml`, `plugin.json` and `engine/showrunner/__init__.py`.
2. `python scripts/build_dist.py`, then `python scripts/smoke_dist.py`.
3. Create a GitHub release with a tag like `v0.1.0`. Attach everything in `dist/`: one zip per skill, the all-skills zip, and `SHA256SUMS`. People on ChatGPT will upload these zips, so a release page is their install page.
4. Say in the release notes what was and was not tested. The README has the list.

## After launch

Answer every issue and every comment inside a day for the first two weeks. This matters more than the launch post. Thank the first person who reports a wrong fact, fix it in public and credit them.

Do not buy stars or trade them. GitHub removes fake activity, and a repo with bought stars and no users is easy to spot.

Watch what people actually run. If most issues are about one skill, that is the real product, so make that skill excellent before adding a twenty-fifth.

Re-check the platform facts every month. `showrunner stale` lists the ones past 90 days. A repo whose facts are dated and current is rare, and it is the main reason to trust this one.
