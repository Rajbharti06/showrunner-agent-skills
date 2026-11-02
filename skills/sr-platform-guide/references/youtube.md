# YouTube

_Generated from the Showrunner data files by `scripts/gen_refs.py`. Do not edit by hand. Fix the data and regenerate._

Statuses: official, reported, inferred, study. Confidence: high, medium, low. Platforms change often, so anything old should be checked in the live app (`facts_stale`).

## YouTube

**How people find content here (maintainer summary):** search and recommendation; videos keep earning for years.

**Maintainer's view (an opinion, not a fact):** Best for depth and for content that keeps earning. Shorts are a fast on-ramp; long-form is where trust builds.

**Format fit, maintainer priors from 1 to 5 (opinions you can edit in `fit.json`):**

| Format | Fit |
|---|---|
| Short video | 4 |
| Long video | 5 |
| Carousel or document | 1 |
| Text | 1 |
| Live | 3 |

**What to measure:**

- Short: 'How many chose to view' (share who watched rather than swiped away)
- Long: click-through rate and average percentage viewed, per video
- Subscribers gained per 1,000 views

**Facts in the database (as of 2026-11-02):**

| Id | Claim | Status | Confidence | Source |
|---|---|---|---|---|
| `youtube.description.max_chars` | Descriptions can be up to 5,000 characters. | official | high | YouTube long-standing limit |
| `youtube.hashtags.cap` | With more than 15 hashtags on a video, YouTube ignores all of them. | official | high | YouTube Help, long-standing |
| `youtube.title.max_chars` | Titles can be up to 100 characters. | official | high | YouTube long-standing limit |
| `youtube.shorts.max_seconds` | Square or vertical videos up to three minutes can be Shorts. | reported | medium | [OutlierKit, 3 Oct 2026](https://outlierkit.com/resources/youtube-shorts-algorithm/) |
| `youtube.ranking.unpublished` | YouTube has not published its ranking signals or their weights. What you control is packaging and retention. | inferred | medium | OutlierKit and vidIQ reading, Oct 2026 |
| `youtube.shorts.chose_to_view` | Shorts analytics show 'How many chose to view': the share of times people watched rather than swiped away. | reported | medium | [OutlierKit, 3 Oct 2026](https://outlierkit.com/resources/youtube-shorts-algorithm/) |
| `youtube.shorts.engaged_view` | A Short 'engaged view' is described as clicking to watch or watching past the initial seconds. | reported | low | [OutlierKit, 3 Oct 2026](https://outlierkit.com/resources/youtube-shorts-algorithm/) |
| `youtube.ai_disclosure` | YouTube requires creators to disclose realistic AI-generated or altered content, using the AI use setting (Yes or No) when uploading in YouTube Studio. | official | high | [YouTube Help, Disclosing use of altered or synthetic content](https://support.google.com/youtube/answer/14328491) |
| `youtube.originality.2026_10` | From 1 Oct 2026 YouTube says it is updating its systems to further prioritize original content, which reduces reach for re-uploads that add nothing of the creator's own. | reported | medium | [OutlierKit, 3 Oct 2026](https://outlierkit.com/resources/youtube-shorts-algorithm/) |
| `youtube.test_and_compare` | YouTube Studio's Test & compare can test thumbnails, and since July 2025 titles too. | reported | medium | [Tubefilter, 16 Jul 2025](https://www.tubefilter.com/2025/07/16/youtube-feature-test-and-compare-titles-thumbnails/amp/) |

## What nobody outside the company knows

The exact ranking weights. Where a platform has published a list of signals but not weights, the table above says so. Treat any advice that quotes exact percentages as a guess unless it links to a primary source.
