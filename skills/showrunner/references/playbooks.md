# Playbook catalogue

_Generated from the Showrunner data files by `scripts/gen_refs.py`. Do not edit by hand. Fix the data and regenerate._

Start one with `playbook_start` (CLI `python scripts/sr.py playbook start <id>`). Gates: `approve` means show the work and wait for a yes. `human` means the person does it outside the chat. `data` means the person brings numbers. `auto` means the assistant can do it.

## Two-week campaign (`campaign-sprint`)

One offer, one audience, one call to action. Teaser, proof, objections, offer, last call.

Duration: 14 days. Use when: You are launching something: a product, a course, a service, a video series, an application round.

| # | Step | Skill | Gate | Produces |
|---|---|---|---|---|
| 1 | Define the offer | `sr-strategy` | approve | brief |
| 2 | Map the objections | `sr-strategy` | approve | objection map |
| 3 | Plan the arc | `sr-calendar` | approve | campaign calendar |
| 4 | Produce the assets | `sr-hook` | approve | assets |
| 5 | Check claims and disclosure | `sr-policy-check` | approve | checked assets |
| 6 | Launch | `showrunner` | human | live campaign |
| 7 | Follow up | `sr-engage` | human | conversations |
| 8 | Debrief | `sr-audit` | data | debrief |

## Monthly review (`monthly-review`)

Export, post-mortem, outliers in your own work, experiments, platform changes, calibration, strategy update, next calendar.

Duration: 2 hours. Use when: Once a month, every month.

| # | Step | Skill | Gate | Produces |
|---|---|---|---|---|
| 1 | Export the month | `showrunner` | data | exports |
| 2 | Post-mortem | `sr-audit` | approve | post-mortem |
| 3 | Your own outliers | `sr-outliers` | approve | patterns |
| 4 | Review experiments | `sr-growth-loop` | approve | decisions |
| 5 | Check what changed on the platforms | `sr-research` | approve | change list |
| 6 | Calibrate the hook score | `sr-growth-loop` | approve | weights |
| 7 | Update the strategy | `sr-strategy` | approve | strategy |
| 8 | Next month's calendar | `sr-calendar` | approve | calendar |

## One source, many pieces (`one-to-many`)

Find the best clips, cut, caption, adapt per platform, add text and carousel derivatives, check originality, schedule.

Duration: 1 to 2 days. Use when: You have a long video, podcast, talk or article and want a week of content from it.

| # | Step | Skill | Gate | Produces |
|---|---|---|---|---|
| 1 | Bring the source | `sr-repurpose` | data | transcript |
| 2 | Find the clips | `sr-repurpose` | approve | clip list |
| 3 | Cut list and captions | `sr-edit-plan` | human | cut clips |
| 4 | Hook and caption per platform | `sr-hook` | approve | copy |
| 5 | Text and carousel derivatives | `sr-text-post` | approve | derivatives |
| 6 | Humanize and originality check | `sr-policy-check` | approve | checked pieces |
| 7 | Spread across the week | `sr-calendar` | approve | calendar |

## Profile makeover (`profile-makeover`)

Audit each profile, write one positioning line, rewrite everywhere, choose pinned content.

Duration: 1 day. Use when: Your profiles do not say who you help or why to follow.

| # | Step | Skill | Gate | Produces |
|---|---|---|---|---|
| 1 | Audit every profile | `sr-profile-audit` | approve | scores |
| 2 | Write the positioning line | `sr-strategy` | approve | line |
| 3 | Rewrite name, bio, link | `sr-profile-audit` | approve | new profile copy |
| 4 | Choose pinned content | `sr-ideas` | approve | pins |
| 5 | Apply the changes | `showrunner` | human | updated profiles |
| 6 | Re-audit | `sr-profile-audit` | approve | new scores |

## Weekly content sprint (`weekly-sprint`)

Check last week, pick ideas, hooks, scripts, packaging, clean-up, adapt for spokes, schedule, publish, engage, log.

Duration: one week. Use when: Every week once the plan is set.

| # | Step | Skill | Gate | Produces |
|---|---|---|---|---|
| 1 | Read last week | `sr-audit` | data | last-week read |
| 2 | Pick this week's ideas | `sr-ideas` | approve | ideas |
| 3 | Hooks | `sr-hook` | approve | hooks |
| 4 | Scripts or copy | `sr-script` | approve | drafts |
| 5 | Titles, captions, keywords | `sr-title-thumbnail` | approve | packaging |
| 6 | Humanize and policy check | `sr-humanize` | approve | final copy |
| 7 | Edit plan | `sr-edit-plan` | human | edited video |
| 8 | Adapt for spokes | `sr-repurpose` | approve | spoke versions |
| 9 | Update the calendar | `sr-calendar` | approve | calendar |
| 10 | Publish | `showrunner` | human | published posts |
| 11 | Engage for 48 hours | `sr-engage` | human | engagement |
| 12 | Log it | `sr-growth-loop` | data | log |

## YouTube video launch (`youtube-video-launch`)

Validate the topic, design the title and thumbnail first, script for retention, edit, upload, test, read the curve.

Duration: 3 to 7 days. Use when: You are making a long-form YouTube video and want the packaging and retention right.

| # | Step | Skill | Gate | Produces |
|---|---|---|---|---|
| 1 | Validate the topic | `sr-seo` | approve | keyword + proof |
| 2 | Title and thumbnail first | `sr-title-thumbnail` | approve | packaging |
| 3 | Script for retention | `sr-script` | approve | script |
| 4 | Edit plan | `sr-edit-plan` | human | edit |
| 5 | Description, chapters, tags | `sr-seo` | approve | metadata |
| 6 | Humanize and policy check | `sr-policy-check` | approve | checked |
| 7 | Upload and set up Test & compare | `showrunner` | human | published video |
| 8 | Read the curve at 48 hours | `sr-audit` | data | retention read |
| 9 | Log the lesson | `sr-growth-loop` | data | log |

## Zero to your first 1,000 (`zero-to-first-1000`)

Intake, positioning, voice, profile, research, first batch of content, a four-week calendar, and a day-30 review. One hub platform first.

Duration: 30 days. Use when: You are starting a channel or account and want a plan you can actually finish.

| # | Step | Skill | Gate | Produces |
|---|---|---|---|---|
| 1 | Run the intake | `showrunner` | approve | profile.json |
| 2 | Write the promise and the pillars | `sr-strategy` | approve | positioning + pillars |
| 3 | Capture your voice | `sr-voice` | approve | voice notes |
| 4 | Set up the hub profile | `sr-profile-audit` | approve | profile rewrite |
| 5 | Study what works in your niche | `sr-research` | approve | niche map |
| 6 | Rank outliers | `sr-outliers` | data | swipe file |
| 7 | Build the idea bank | `sr-ideas` | approve | scored ideas |
| 8 | Write the hooks | `sr-hook` | approve | hooks |
| 9 | Script the first batch | `sr-script` | approve | scripts |
| 10 | Package it | `sr-caption` | approve | captions + titles |
| 11 | Clean and check | `sr-humanize` | approve | final copy |
| 12 | Lay out four weeks | `sr-calendar` | approve | calendar |
| 13 | Publish week one | `showrunner` | human | published posts |
| 14 | Run the engagement routine | `sr-engage` | human | engagement log |
| 15 | Week-one numbers | `sr-audit` | data | first read |
| 16 | Choose one thing to test | `sr-growth-loop` | approve | experiment |
| 17 | Run two weekly sprints | `showrunner` | human | six to twelve posts |
| 18 | Day-30 review | `sr-growth-loop` | approve | decision |
