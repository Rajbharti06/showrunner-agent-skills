# The 24 skills

_Generated from the Showrunner data files by `scripts/gen_refs.py`. Do not edit by hand. Fix the data and regenerate._

Every skill works without code, by following the method written in it. Where there is a tool, the skill names it.

## Orchestrate

| Skill | What it does | Tools |
|---|---|---|
| [`showrunner`](../skills/showrunner/SKILL.md) | Conductor for growing a channel on Instagram, YouTube, TikTok, Facebook, LinkedIn, X or Threads. | `intake_recommend`, `facts_search`, `calibrate_run`, `playbook_list`, `playbook_show`, `playbook_next`, `playbook_done`, `playbook_status`, `profile_get`, `profile_save`, `skill_list`, `skill_get`, `doctor` |
| [`sr-intake`](../skills/sr-intake/SKILL.md) | Asks a creator what they want to make, who it is for, where it will go, what they want out of it, where they are now, how many hours a week they really have and whether they will be on camera, then recommends one hub platform, one or two spokes, what to skip for now, a weekly load that fits their hours, and a first seven days. | `intake_questions`, `intake_recommend`, `profile_save` |
| [`sr-strategy`](../skills/sr-strategy/SKILL.md) | Builds a creator's positioning and content strategy as a one-page brief: who they help, the one-sentence promise, three content pillars, the proof they can actually show, the single call to action, and what to stop doing. | `ideas_matrix`, `profile_get`, `profile_save` |
| [`sr-voice`](../skills/sr-voice/SKILL.md) | Captures how a creator actually writes and talks so every later draft sounds like them and not like a generic assistant. | `profile_save` |

## Research

| Skill | What it does | Tools |
|---|---|---|
| [`sr-research`](../skills/sr-research/SKILL.md) | Maps a niche without scraping anything. | `facts_search`, `facts_stale` |
| [`sr-outliers`](../skills/sr-outliers/SKILL.md) | Ranks posts by how far each one beat its own account's median, so a small account's breakout is not buried under a giant's average. | `outliers_rank` |
| [`sr-ideas`](../skills/sr-ideas/SKILL.md) | Builds a bank of content ideas from the creator's pillars and real experience, scores each one on pain, proof, novelty, fit and effort, flags near-duplicates, and picks the first batch. | `ideas_score`, `ideas_matrix` |
| [`sr-profile-audit`](../skills/sr-profile-audit/SKILL.md) | Scores a social profile out of 100 and rewrites it: name and handle, searchable keywords, the one-line promise, bio, link, avatar and banner, pinned or featured content, and platform extras. | `facts_search`, `profile_save` |

## Make

| Skill | What it does | Tools |
|---|---|---|
| [`sr-hook`](../skills/sr-hook/SKILL.md) | Writes and scores hooks, the first line, first three seconds or first frame that decides whether anyone keeps watching or reading. | `hook_score`, `hook_formulas`, `calibrate_run` |
| [`sr-script`](../skills/sr-script/SKILL.md) | Writes and times scripts for short vertical video and long YouTube videos. | `script_beats` |
| [`sr-title-thumbnail`](../skills/sr-title-thumbnail/SKILL.md) | Designs a YouTube title and thumbnail as one message in two places. | `title_score`, `facts_search`, `experiment_log` |
| [`sr-caption`](../skills/sr-caption/SKILL.md) | Writes and checks captions and descriptions for Instagram, TikTok, YouTube, Facebook, LinkedIn, X and Threads. | `caption_check`, `facts_search` |
| [`sr-carousel`](../skills/sr-carousel/SKILL.md) | Plans swipeable carousels and document posts for Instagram, LinkedIn, Facebook and TikTok photo mode. | `facts_search` |
| [`sr-text-post`](../skills/sr-text-post/SKILL.md) | Writes text posts and threads for LinkedIn, X, Threads and Facebook. | `caption_check`, `text_humanize`, `facts_search` |
| [`sr-edit-plan`](../skills/sr-edit-plan/SKILL.md) | Turns a video and its transcript into an edit plan. | `script_beats`, `subtitles_analyze`, `subtitles_rechunk` |
| [`sr-repurpose`](../skills/sr-repurpose/SKILL.md) | Turns one long video, podcast, talk or article into a week of native pieces. | `subtitles_rechunk`, `clips_find`, `facts_search` |
| [`sr-humanize`](../skills/sr-humanize/SKILL.md) | Edits a draft so it sounds like the person and not like a generic assistant. | `text_humanize`, `text_detect` |

## Check and prepare

| Skill | What it does | Tools |
|---|---|---|
| [`sr-policy-check`](../skills/sr-policy-check/SKILL.md) | The last check before anything goes live. | `facts_search` |
| [`sr-seo`](../skills/sr-seo/SKILL.md) | Finds the phrases people actually search for and puts them in the right places on YouTube, TikTok, Instagram and Google. | `title_score`, `caption_check`, `facts_search` |
| [`sr-calendar`](../skills/sr-calendar/SKILL.md) | Builds a content calendar sized to the hours the person actually has. | `calendar_build`, `playbook_start`, `profile_get` |
| [`sr-platform-guide`](../skills/sr-platform-guide/SKILL.md) | A sourced, dated field guide to YouTube, Instagram, TikTok, Facebook, LinkedIn, X and Threads. | `facts_search`, `facts_stale` |

## Learn

| Skill | What it does | Tools |
|---|---|---|
| [`sr-engage`](../skills/sr-engage/SKILL.md) | Handles the replies, comments, DMs and outreach that happen after a post goes up. | `text_humanize` |
| [`sr-audit`](../skills/sr-audit/SKILL.md) | Reads a creator's own numbers honestly. | `outliers_rank`, `retention_read`, `calibrate_run` |
| [`sr-growth-loop`](../skills/sr-growth-loop/SKILL.md) | Runs the learning loop that makes a channel get better over time. | `calibrate_run`, `experiment_new`, `experiment_log`, `experiment_review`, `profile_save` |
