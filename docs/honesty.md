# What is and is not validated

Showrunner makes a lot of numbers. This page says what each one is, where it comes from, and how much to trust it. The short version: **none of the scores predict views, and the tool is built to say so.**

## The scorers

| What | How it works | How far to trust it |
|---|---|---|
| **Hook score** (`hook_score`) | Six regex-and-count checks on the text: specificity (numbers, names, places), front-loading, addressing the viewer, curiosity, stakes, brevity. Default weights 0.30, 0.20, 0.15, 0.15, 0.10, 0.10. Dealbreakers such as greetings cap the score at 35 | A way to rank options and find the weak part. Not validated against views. It cannot see delivery, the first frame or the edit. The dealbreaker and filler patterns are English: a Hindi greeting such as "दोस्तों," is not caught |
| **Title score** (`title_score`) | Length, keyword placement, specificity, and a penalty of 8 points for each hard flag such as shouting or bait phrases | Same. Written for YouTube-style titles |
| **Caption check** (`caption_check`) | Length, preview cut, concrete detail in the visible window, hashtag count, number of asks, search terms, links, stock phrases | Mostly rules about the platform, so as good as the facts under it. Preview lengths marked "inferred" are guides |
| **Beat sheet** (`script_beats`) | Times each sentence at your speaking pace and flags long single lines, dense lines, stretches with no number, name or turn, a missing loop, an early call to action | Flags to check, not verdicts |
| **Clip finder** (`clips_find`) | Scores sliding windows of the transcript: 35% hook, 15% self-contained, 20% density, 15% payoff, 10% pace, 5% length | Reads only the words. Watch every clip before you cut it |
| **Retention reader** (`retention_read`) | Finds the shape of your curve (front-loaded cliff, loop-friendly, mid-video cliff or steady decay), cliffs, and rewatch bumps. Ignores the last 8% of a video, which always falls off | Thresholds are rules of thumb. Good at describing a curve, not at telling you why |
| **Outlier rank** (`outliers_rank`) | Multiple of each post's views over its own account's median | Solid arithmetic. Under 2x on a small sample is noise |
| **Idea score** (`ideas_score`) | Weighted sum of five ratings you give: pain 30%, proof 25%, novelty 15%, fit 15%, ease 15% | It is your judgement written down, with the math done for you |
| **Platform fit** (`intake_recommend`) | 1 to 5 priors per platform, goal, audience and format, from [`fit.json`](../engine/showrunner/data/fit.json) | The maintainer's opinions. Edit them. The output says "starting hypothesis, not a prediction" |
| **Effort estimates** (`calendar_build`) | Minutes per format (long video 360, short video 70, carousel 55, text post 15, story 10), 30% to adapt a piece, 15% held back for replies, 20% off when three or more of a format are made together | Planning estimates. Replace them after two weeks with your own times |

## The check that tests the scorers

`calibrate_run` takes a table of your own posts (hook text and views). It splits them at your median into winners and misses, then asks for each check how often a winner out-scores a miss. That is an AUC, with a 90% bootstrap interval. An AUC of 0.5 is a coin flip.

- It needs at least 8 posts to run and **30 to write new weights**. Below that it tells you the answer is not stable yet.
- It only writes weights if at least one check is above chance, and only when you pass `write_weights`.
- It describes one account. A result for you is not a result for anyone else.
- On the invented example data in `examples/posts.csv`, the specificity check separates winners (AUC 0.70) and the total score does not (interval includes 0.5). The tool prints exactly that.

## Experiments

`experiment_review` compares two variants with a rank-sum permutation test. It makes no assumption about how views are distributed. It reports a p-value and the ratio of medians, and says "adopt" only if p is under 0.1 and the ratio is at least 1.2. Under four posts per variant it says "not enough posts". The thresholds are the maintainer's choice. With four posts per variant only large effects can show up. "No clear difference" at small n means "cannot tell".

## Facts

Every entry in [`facts.json`](../engine/showrunner/data/facts.json) has:

| Field | Meaning |
|---|---|
| `status` | `official` (the platform says it), `reported` (someone other than the platform says it: a news outlet, a vendor blog, an executive quoted second-hand), `inferred` (a reasonable reading of indirect evidence), `study` (one analysis, correlation not proof) |
| `confidence` | high, medium or low |
| `source`, `url` | Where it came from. `url` is a primary link where one was verified |
| `as_of` | The day it was last checked. After 90 days `facts_stale` flags it |

Some official limits do not have a verified link yet. `showrunner doctor` counts them, and adding the link is the easiest pull request there is.

What the database does **not** contain: exact ranking weights for any platform. YouTube has not published its ranking signals. TikTok lists kinds of signals, not weights. LinkedIn has not published weights. X published code in 2026, and reports of the weights disagree on detail. Anyone quoting exact percentages for these without a primary source is guessing.

## The humanizer

`text_humanize` and `text_detect` are a style editor and a style check. They remove invisible characters, em dashes and curly quotes, cut or swap stock phrases, and list habits a script cannot fix. They do **not** test or claim to beat any AI detector, because detectors are unreliable and that is not the goal. If a platform, school or employer requires you to disclose AI use, disclose it.

## What it never does

- Post, schedule or send anything. Every skill ends at a draft.
- Invent your story, numbers or results. It asks for them.
- Read your files over MCP unless you turn that on.
- Send your data anywhere. The engine makes no network calls. State is kept in `~/.showrunner`.

## Found something wrong?

Open an issue or a pull request. A correction with a primary source link is the most valuable contribution this project can get. See [CONTRIBUTING.md](../CONTRIBUTING.md).
