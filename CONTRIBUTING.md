# Contributing

Thanks for helping. The project lives or dies on whether people can trust what it says about platforms, so the most valuable contribution is a correct, sourced fact.

## Fact PRs (start here)

Platform facts live in [`engine/showrunner/data/facts.json`](engine/showrunner/data/facts.json). One entry looks like this:

```json
{
  "id": "youtube.hashtags.cap",
  "platform": "youtube",
  "topic": "limits",
  "claim": "With more than 15 hashtags on a video, YouTube ignores all of them.",
  "value": null,
  "status": "official",
  "source": "YouTube Help, long-standing",
  "url": null,
  "primary": null,
  "confidence": "high",
  "as_of": "2026-11-02",
  "note": ""
}
```

Rules:

1. **Status must be honest.** `official` means the platform itself states it, and you link that page. `reported` means someone else reports it (a news outlet, a vendor, an executive quoted second-hand) and you link them. `inferred` is a reasonable reading of indirect evidence. `study` is one analysis.
2. **`reported` and `study` need a `url`** (the check fails without one). `inferred` needs a `note` saying what it is inferred from. `official` should have a `url` too, but a number of official limits still do not, and `showrunner doctor` counts them. Adding a verified primary link to one of those is the easiest first contribution.
3. **Set `as_of` to the day you checked**, and set `confidence` to what you actually have.
4. **Write the claim as the source says it.** No rounding up, no extra reasoning. Put your reasoning in `note`.
5. **No exact ranking weights without a primary source.**
6. If you change a fact, search the skills for its id (`grep -rn "youtube.hashtags.cap" skills`) and update the text that quotes it.

Then run `python scripts/gen_refs.py` to regenerate the platform guides, and the checks below.

## Other contributions

- **A skill fix or a new skill.** Each skill is `skills/<name>/SKILL.md`. Keep the body under about 5,000 tokens. The `description` must say when to use it (under 1,024 characters). Every skill must be useful without code, and must name any tool it uses. Do not add a skill that duplicates one that exists.
- **A better scorer.** Show how it does on `calibrate_run` against real posts you are allowed to share, or say it is untested.
- **A bug.** Include the command, the input if you can share it, and what you expected.
- **A report from a platform that did not load the skills.** Tell us the tool, the plan and what happened. This is very useful.

## Before you open a PR

```
python -m unittest discover -s tests
python scripts/validate_skills.py
python scripts/lint_prose.py
python scripts/sync_shims.py --check
python scripts/gen_refs.py --check
```

All five must pass. CI runs the same on Python 3.9 to 3.13. If you edit `scripts/sr_shim.py`, run `python scripts/sync_shims.py` so every skill gets the copy. If you edit data files that feed generated docs, run `python scripts/gen_refs.py`.

`validate_skills.py` checks the spec and also checks that every tool, parameter, CLI example, fact id and skill name mentioned in a `SKILL.md` is real, so a skill cannot promise something the engine cannot do.

## House rules for the writing

The writing in this repo follows the same rules the humanizer enforces. No em dashes (the linter fails the build). Plain words and short sentences. No inflated claims: say what was tested and what was not. No bullet points where a sentence would do. Do not copy text from other projects.

## Code rules

Python 3.9 compatible, standard library only. No network calls in the engine. Tools return `{"ok", "text", "data"}`. Anything that writes to disk is marked `stateful` so the HTTP server hides it by default. Tests for every bug fixed.

## Be kind

Assume good faith. Disagree about the work, not the person.
