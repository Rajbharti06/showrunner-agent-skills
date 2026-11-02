# Instagram

_Generated from the Showrunner data files by `scripts/gen_refs.py`. Do not edit by hand. Fix the data and regenerate._

Statuses: official, reported, inferred, study. Confidence: high, medium, low. Platforms change often, so anything old should be checked in the live app (`facts_stale`).

## Instagram

**How people find content here (maintainer summary):** recommendation plus your followers; strong for visual and carousel.

**Maintainer's view (an opinion, not a fact):** Reels for reach, carousels for saves and sends, Stories and DMs for relationship.

**Format fit, maintainer priors from 1 to 5 (opinions you can edit in `fit.json`):**

| Format | Fit |
|---|---|
| Short video | 4 |
| Long video | 1 |
| Carousel or document | 5 |
| Text | 2 |
| Live | 3 |

**What to measure:**

- Sends per reach (one of the three video signals Mosseri named: watch time, likes per reach, sends per reach)
- Watch time and average watch time on Reels
- Saves per reach on carousels

**Facts in the database (as of 2026-11-02):**

| Id | Claim | Status | Confidence | Source |
|---|---|---|---|---|
| `instagram.caption.max_chars` | Captions can be up to 2,200 characters. | official | high | Instagram long-standing limit |
| `instagram.hashtags.cap` | Instagram caps hashtags at five per post. | reported | medium | [PostEverywhere, Oct 2026](https://posteverywhere.ai/blog/how-the-instagram-algorithm-works) |
| `instagram.preview.chars` | Roughly the first 125 characters of a caption show before 'more'. | inferred | low | Widely cited, varies by device |
| `instagram.reels.max_seconds` | Reels can be up to three minutes. | reported | medium | [Social Media Today, Jan 2025](https://www.socialmediatoday.com/news/instagram-officially-expands-reels-length-to-3-minutes/737766/) |
| `instagram.hashtags.distribution` | Mosseri said he would not think of hashtags as a way to get more distribution. | reported | medium | [PostEverywhere citing Hootsuite](https://posteverywhere.ai/blog/how-the-instagram-algorithm-works) |
| `instagram.signals.top_three` | Adam Mosseri named watch time, likes per reach and sends per reach as the top ranking signals for video. | reported | medium | [PostEverywhere citing Social Media Today, Jan 2025](https://posteverywhere.ai/blog/how-the-instagram-algorithm-works) |
| `instagram.originality.2026_04` | As of April 2026, Instagram no longer recommends accounts that regularly repost content they did not create, now including photos and carousels. | reported | medium | [PostEverywhere citing TechCrunch](https://posteverywhere.ai/blog/how-the-instagram-algorithm-works) |
| `instagram.paid_partnership` | Instagram's branded content policies require the paid partnership label to tag the featured brand. | official | high | [Instagram Help, paid partnership label for organic branded content](https://help.instagram.com/android-app/1109894795810258) |
| `instagram.your_algorithm` | 'Your Algorithm' lets people tune Reels recommendations. Launched for Reels in the US in December 2025. | reported | low | [PostEverywhere, Oct 2026](https://posteverywhere.ai/blog/how-the-instagram-algorithm-works) |

## What nobody outside the company knows

The exact ranking weights. Where a platform has published a list of signals but not weights, the table above says so. Treat any advice that quotes exact percentages as a guess unless it links to a primary source.
