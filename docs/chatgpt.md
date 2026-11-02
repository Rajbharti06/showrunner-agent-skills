# Use Showrunner in ChatGPT

There are three ways, from easiest to most hands-on. None of them has been tested by the maintainers inside ChatGPT, because they were written to ChatGPT's published formats without an account on every plan. If a step does not match what you see, open an issue with a screenshot and it will be fixed.

## 1. Upload the skills (recommended)

ChatGPT loads Agent Skills (`SKILL.md`). As documented in November 2026: upload a ZIP through Plugins, then Skills, then Create, then Upload, on paid plans except Free and Go. On Enterprise and Edu, an admin has to turn Skills on first. See `showrunner facts --id tooling.chatgpt.skills` for the source and date.

1. Get the zips: run `python scripts/build_dist.py` in a checkout, or download them from the release page. You get one zip per skill in `dist/skills/` and one for everything.
2. Upload `showrunner.zip` first. It is the conductor, and it asks the first questions.
3. Upload the skills you want to use alongside it. Start with `sr-intake`, `sr-hook`, `sr-script` and `sr-caption`, then add more.
4. Start a chat and say: *I want to grow my channel.*

Each zip contains the skill and a small bundled copy of the engine, so the scoring tools can run if your ChatGPT plan can run Python. If it cannot, every skill still works by following the method written in it.

## 2. Build a Custom GPT

If you cannot upload skills, a Custom GPT can hold the conductor's behaviour. Files for this are in [`gpt/`](../gpt):

- `gpt/instructions.md` goes in the Instructions box (it is under the 8,000 character limit)
- `gpt/knowledge-files.md` lists which files to upload as Knowledge
- turn on Code Interpreter, and upload `showrunner-all-skills.zip` as a Knowledge file so the model can unzip it and run `scripts/sr.py`

A Custom GPT follows instructions less reliably than a loaded skill does, so expect to nudge it back to the questions now and then.

## 3. Connect the MCP server

ChatGPT can call remote MCP servers in Developer Mode (beta). The setup, and its limits, are in [mcp/README.md](../mcp/README.md). It needs a public HTTPS address, which means a tunnel, and it is the least tested path. Prefer 1 or 2.

## What to expect

The assistant asks what you want to make, for whom and where, recommends one main platform and one or two secondary ones sized to your real weekly hours, and then walks you through a playbook. It writes drafts and plans. It never posts for you.

## Privacy

Your profile, playbook runs and experiment logs live in a folder on the machine that runs the engine. In ChatGPT's sandbox that folder does not persist between chats unless the platform keeps it, so ask the assistant to print your profile at the end of a session and paste it back at the start of the next.
