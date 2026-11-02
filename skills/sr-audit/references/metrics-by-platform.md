# Metrics by platform

_Generated from the Showrunner data files by `scripts/gen_refs.py`. Do not edit by hand. Fix the data and regenerate._

Use the number that matches the goal. Views alone rarely do. Compare each post with the same account's median, not with other accounts (`sr-audit`).

## YouTube

- Short: 'How many chose to view' (share who watched rather than swiped away)
- Long: click-through rate and average percentage viewed, per video
- Subscribers gained per 1,000 views

Signals the platform or reports describe, with status:

- `youtube.shorts.chose_to_view` (reported, medium confidence): Shorts analytics show 'How many chose to view': the share of times people watched rather than swiped away.
- `youtube.shorts.engaged_view` (reported, low confidence): A Short 'engaged view' is described as clicking to watch or watching past the initial seconds.
- `youtube.ranking.unpublished` (inferred, medium confidence): YouTube has not published its ranking signals or their weights. What you control is packaging and retention.

## Instagram

- Sends per reach (one of the three video signals Mosseri named: watch time, likes per reach, sends per reach)
- Watch time and average watch time on Reels
- Saves per reach on carousels

Signals the platform or reports describe, with status:

- `instagram.signals.top_three` (reported, medium confidence): Adam Mosseri named watch time, likes per reach and sends per reach as the top ranking signals for video.
- `instagram.hashtags.distribution` (reported, medium confidence): Mosseri said he would not think of hashtags as a way to get more distribution.

## TikTok

- Completion rate and average watch time
- Shares per view
- Profile visits per 1,000 views

Signals the platform or reports describe, with status:

- `tiktok.signals.published` (reported, medium confidence): TikTok's explainers list interactions (watch time, completion, replays, likes, comments, shares, follows, 'not interested'), video information and user or device settings. Weights are not published.
- `tiktok.search.inputs` (inferred, low confidence): Search is described as using caption keywords, hashtags, on-screen text and spoken words.
- `tiktok.completion.threshold` (inferred, low confidence): Third-party analyses claim 75 to 100 percent completion triggers aggressive distribution.

## Facebook

- 3-second and 1-minute views on Reels
- Shares and saves
- Group or page follows gained per post

Signals the platform or reports describe, with status:

- `facebook.true_interest_survey` (reported, low confidence): Meta is testing a 1 to 5 interest-match survey after Reels. Low ratings count as negative even when watch time is high.

## LinkedIn

- Comments (depth, not count), and how early they arrive
- Impressions per post against your own median
- Profile views and inbound messages

Signals the platform or reports describe, with status:

- `linkedin.signals.modelled` (inferred, low confidence): Early engagement, comment depth and dwell time are widely modelled as ranking inputs. LinkedIn has not published weights.
- `linkedin.carousel.study` (study, low confidence): Metricool's study of 600,000+ posts found carousels drew about 17x the interactions of images.

## X

- Replies and quotes per post
- Profile visits per post
- Follows per 100 posts

Signals the platform or reports describe, with status:

- `x.ranking.open_source` (reported, medium confidence): X published its For You ranking code in August 2026 (xai-org, Apache 2.0). Reported weights: reply, quote and DM share 5, copy-link about 20, follow 4, repost 1, like 0.5. Negative signals (report, mute, not interested, block) weigh far more. Weights apply to predicted probabilities, not raw counts. Posts older than 48 hours are filtered.

## Threads

- Replies per post
- Reposts per post
- Follows per 100 posts

## Reading them

- A rate (per view, per reach, per 1,000 views) beats a count.
- A share of viewers who stayed beats the average view time on its own, because a few long watchers can lift an average.
- Read at least ten posts before calling a pattern, and four per variant before calling a test (`sr-growth-loop`).
- Write down what each metric means before you read it. "Engaged view" and "chose to view" are not the same thing.
