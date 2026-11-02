# MCP tools

_Generated from the Showrunner data files by `scripts/gen_refs.py`. Do not edit by hand. Fix the data and regenerate._

34 tools. Over stdio all are available. Over HTTP the 25 marked read-only are available by default; tools that save to the local folder need `--stateful` and a single trusted user.

| Tool | CLI command | Saves to disk | What it does |
|---|---|---|---|
| `intake_questions` | `showrunner questions` | no | The questions to ask before recommending anything. |
| `intake_recommend` | `showrunner intake` | no | Turn the answers into a hub, spokes, weekly load and first 7 days. |
| `hook_score` | `showrunner hook` | no | Score hooks for first-seconds strength and say what to fix. |
| `hook_formulas` | `showrunner hook-shapes` | no | List proven hook shapes with a fill-in template. |
| `title_score` | `showrunner title` | no | Score YouTube titles (and check them against thumbnail text). |
| `script_beats` | `showrunner beats` | no | Time a script and flag hooks that run long and dead stretches. |
| `caption_check` | `showrunner caption` | no | Check a caption against a platform's limits and preview cut. |
| `text_humanize` | `showrunner humanize` | no | Clean AI-sounding patterns out of a draft. |
| `text_detect` | `showrunner detect` | no | Style check: burstiness, specificity, stock phrases, fingerprints. |
| `outliers_rank` | `showrunner outliers` | no | Rank posts by how far they beat their own account's median. |
| `retention_read` | `showrunner retention` | no | Find the cliffs and rewatch bumps in a retention curve. |
| `subtitles_analyze` | `showrunner subtitles` | no | Words per minute, dead air and filler words from an SRT or VTT. |
| `subtitles_rechunk` | `showrunner rechunk` | no | Re-time subtitles into short punchy lines for vertical video. |
| `clips_find` | `showrunner clips` | no | Find the best vertical clips in a long video's transcript. |
| `calendar_build` | `showrunner calendar` | no | Build a content calendar that fits real weekly hours. |
| `ideas_score` | `showrunner ideas` | no | Rank a list of content ideas and flag near-duplicates. |
| `ideas_matrix` | `showrunner matrix` | no | Seed brainstorming with pillar by angle prompts. |
| `facts_search` | `showrunner facts` | no | Look up a platform fact with its source, status and age. |
| `facts_stale` | `showrunner stale` | no | List facts past their review window. |
| `calibrate_run` | `showrunner calibrate` | no | Test whether the hook score separates YOUR winners from your misses. |
| `playbook_list` | `showrunner playbook list` | no | List the orchestration playbooks. |
| `playbook_show` | `showrunner playbook show` | no | Show every step of a playbook. |
| `playbook_start` | `showrunner playbook start` | yes | Start a playbook run and get step one. |
| `playbook_next` | `showrunner playbook next` | yes | Get the next pending step. |
| `playbook_done` | `showrunner playbook done` | yes | Mark a step done and get the next one. |
| `playbook_status` | `showrunner playbook status` | yes | Show progress through a run. |
| `experiment_new` | `showrunner exp new` | yes | Write down a hypothesis before you post. |
| `experiment_log` | `showrunner exp log` | yes | Record one post's result for a variant. |
| `experiment_review` | `showrunner exp review` | yes | Read the experiments with an honest significance check. |
| `profile_get` | `showrunner profile get` | yes | Show the saved creator profile. |
| `profile_save` | `showrunner profile save` | yes | Save or update the creator profile. |
| `skill_list` | `showrunner skills` | no | List the skills in this repo. |
| `skill_get` | `showrunner skill` | no | Read a skill's instructions. |
| `doctor` | `showrunner doctor` | no | Check the install. |
