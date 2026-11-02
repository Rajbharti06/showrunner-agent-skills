# Examples

**Everything in this folder is invented.** The accounts (`@acct_a`, `@demo_creator` and so on), the view counts, the posts, the talk transcript and the retention curve were made up to show how the tools behave. They are not real data and say nothing about any platform or person. `draft.txt` is deliberately written with the habits the humanizer removes.

Run these from the repository root. Each uses the skill's `scripts/sr.py`, which needs only Python 3.9 or newer.

| File | Try it | What you should see |
|---|---|---|
| `hooks.txt` | `python skills/sr-hook/scripts/sr.py hook --file examples/hooks.txt` | Five hooks ranked. The one with a number and a stake scores highest, the greeting is capped by a dealbreaker. |
| `outliers.csv` | `python skills/sr-outliers/scripts/sr.py outliers --file examples/outliers.csv --platform short` | Posts ranked by their multiple over their own account's median, not by raw views. |
| `retention.csv` | `python skills/sr-audit/scripts/sr.py retention --file examples/retention.csv --duration-seconds 45` | A front-loaded cliff: most of the loss happens in the first seven seconds, plus a rewatch bump near the end. |
| `talk.srt` | `python skills/sr-edit-plan/scripts/sr.py subtitles --file examples/talk.srt` | Words per minute, a cut list of dead air with timestamps, and filler words to trim by ear. |
| `talk.srt` | `python skills/sr-repurpose/scripts/sr.py clips --file examples/talk.srt --count 3 --source talk.mp4` | Candidate 9:16 clips with scores and a ready-to-run ffmpeg command each. |
| `talk.srt` | `python skills/sr-edit-plan/scripts/sr.py rechunk --file examples/talk.srt` | The same words re-timed into short lines for vertical video. |
| `ideas.txt` | `python skills/sr-ideas/scripts/sr.py ideas --file examples/ideas.txt` | Ideas ranked on pain, proof, novelty, fit and effort, with near-duplicates flagged and unrated ideas marked. |
| `posts.csv` | `python skills/sr-growth-loop/scripts/sr.py calibrate --file examples/posts.csv` | Whether the hook score separates this account's winners from misses. On this invented data it mostly cannot, and it says so. |
| `draft.txt` | `python skills/sr-humanize/scripts/sr.py humanize --file examples/draft.txt` | Stock phrases cut, the em dash replaced, and a list of habits only a human rewrite can fix. |

## One thing worth noticing

The calibration example is the most important one. The tool does not say "your hook score works". It splits the account's posts at their own median, measures how often the score ranks a winner above a miss, puts a 90% interval around that, and tells you plainly when the interval includes a coin flip. Every scorer in Showrunner is a heuristic until that check says otherwise for your account. See [docs/honesty.md](../docs/honesty.md).

## Using your own numbers

Export a table of your posts from your analytics and save it as CSV with at least the columns `account`, `views` and `hook`. For retention, a CSV with `seconds` and `retention_percent`. For subtitles, any `.srt` or `.vtt` file your editor exports.
