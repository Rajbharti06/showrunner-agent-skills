# X and Threads

_Generated from the Showrunner data files by `scripts/gen_refs.py`. Do not edit by hand. Fix the data and regenerate._

Statuses: official, reported, inferred, study. Confidence: high, medium, low. Platforms change often, so anything old should be checked in the live app (`facts_stale`).

## X

**How people find content here (maintainer summary):** replies and the For You feed; fast, public, conversational.

**Maintainer's view (an opinion, not a fact):** Best for ideas, developer and founder circles, and building in public.

**Format fit, maintainer priors from 1 to 5 (opinions you can edit in `fit.json`):**

| Format | Fit |
|---|---|
| Short video | 2 |
| Long video | 1 |
| Carousel or document | 1 |
| Text | 5 |
| Live | 2 |

**What to measure:**

- Replies and quotes per post
- Profile visits per post
- Follows per 100 posts

**Facts in the database (as of 2026-11-02):**

| Id | Claim | Status | Confidence | Source |
|---|---|---|---|---|
| `x.post.max_chars` | Standard posts are 280 characters. Premium accounts can write much longer posts (up to 25,000). | official | medium | X long-standing limit |
| `x.ranking.open_source` | X published its For You ranking code in August 2026 (xai-org, Apache 2.0). Reported weights: reply, quote and DM share 5, copy-link about 20, follow 4, repost 1, like 0.5. Negative signals (report, mute, not interested, block) weigh far more. Weights apply to predicted probabilities, not raw counts. Posts older than 48 hours are filtered. | reported | medium | [Trending Topics, 17 Aug 2026](https://www.trendingtopics.eu/x-open-sources-its-algorithm-and-reveals-what-it-takes-to-go-viral/) |

## Threads

**How people find content here (maintainer summary):** recommendation of short text; overlaps with Instagram audiences.

**Maintainer's view (an opinion, not a fact):** Low effort if you already post on Instagram. Treat it as a spoke.

**Format fit, maintainer priors from 1 to 5 (opinions you can edit in `fit.json`):**

| Format | Fit |
|---|---|
| Short video | 2 |
| Long video | 1 |
| Carousel or document | 2 |
| Text | 4 |
| Live | 1 |

**What to measure:**

- Replies per post
- Reposts per post
- Follows per 100 posts

**Facts in the database (as of 2026-11-02):**

| Id | Claim | Status | Confidence | Source |
|---|---|---|---|---|
| `threads.post.max_chars` | Posts can be up to 500 characters. | official | high | Threads long-standing limit |

## What nobody outside the company knows

The exact ranking weights. Where a platform has published a list of signals but not weights, the table above says so. Treat any advice that quotes exact percentages as a guess unless it links to a primary source.
