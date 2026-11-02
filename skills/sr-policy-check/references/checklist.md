# Policy checklist

_Generated from the Showrunner data files by `scripts/gen_refs.py`. Do not edit by hand. Fix the data and regenerate._

Not legal advice. Answer each row PASS, FIX or ASK. A row marked ASK means the person has to tell you, or check the live app.

| # | Question | If yes | Facts |
|---|---|---|---|
| 1 | Is there payment, free product, a commission, an affiliate link or a relationship with the company? | Disclose clearly, in words and with the platform label if there is one | `general.ftc_disclosure`, `general.asci_disclosure`, `general.eu_hidden_ads`, `instagram.paid_partnership` |
| 2 | Does the disclosure sit where it cannot be missed (first line, spoken at the start, on screen) and not only among hashtags? | If not, move it | same |
| 3 | Is there realistic AI-generated or AI-altered video, audio, voice or faces? | Use the platform setting or label | `youtube.ai_disclosure`, `tiktok.ai_label` |
| 4 | Is any material reposted from someone else with nothing added? | Add real commentary or analysis, or credit and ask permission, or do not post | `general.originality_trend`, `instagram.originality.2026_04`, `youtube.originality.2026_10`, `facebook.original.2026_04` |
| 5 | Is there music, footage, images or text you do not own or have a licence for? | Use the platform's licensed library or your own media | no verified fact in the database |
| 6 | Does it promise or imply a result (money, health, rank, followers)? | Replace with what happened to you, with numbers, and say it was one case | no verified fact in the database |
| 7 | Does it include a testimonial or review? | Real, current, with permission. Never invent one | no verified fact in the database |
| 8 | Does it show an identifiable person or a child? | Get permission. Take extra care with children | no verified fact in the database |
| 9 | Does the audience or the person live somewhere with extra rules? | Check local rules, or ask a professional | `general.asci_disclosure`, `general.eu_hidden_ads` |

## Policy facts in the database (as of 2026-11-02)

| Id | Claim | Status | Confidence | Source |
|---|---|---|---|---|
| `youtube.originality.2026_10` | From 1 Oct 2026 YouTube says it is updating its systems to further prioritize original content, which reduces reach for re-uploads that add nothing of the creator's own. | reported | medium | [OutlierKit, 3 Oct 2026](https://outlierkit.com/resources/youtube-shorts-algorithm/) |
| `instagram.originality.2026_04` | As of April 2026, Instagram no longer recommends accounts that regularly repost content they did not create, now including photos and carousels. | reported | medium | [PostEverywhere citing TechCrunch](https://posteverywhere.ai/blog/how-the-instagram-algorithm-works) |
| `tiktok.ai_label` | TikTok requires realistic AI-generated content to be labelled and applies its own AI labels. | official | medium | TikTok policy, per Darkroom summary |
| `facebook.original.2026_04` | Meta says it will preferentially promote content filmed or produced directly by the creator or page owner. | reported | medium | [Social Media Examiner, 16 Apr 2026](https://www.socialmediaexaminer.com/facebooks-2026-rules-for-reach-relevance/) |
| `general.originality_trend` | Between April and October 2026, YouTube, Instagram and Facebook each announced changes that favor original content over reposts. | inferred | medium | Our summary of three entries: youtube.originality.2026_10, instagram.originality.2026_04, facebook.original.2026_04 |
| `general.ftc_disclosure` | US FTC rules require a clear disclosure of any material connection to a brand, such as payment or free product. | official | high | [FTC, Disclosures 101 for social media influencers](https://www.ftc.gov/business-guidance/blog/2019/11/disclosures-101-new-ftc-resources-social-media-influencers) |
| `general.asci_disclosure` | In India, ASCI's influencer guidelines require a visible disclosure label when content is a paid or otherwise incentivised promotion. | official | medium | ASCI influencer advertising guidelines |
| `general.eu_hidden_ads` | In the EU, hiding the commercial nature of content is a prohibited unfair commercial practice. | official | medium | EU Unfair Commercial Practices Directive |
| `youtube.ai_disclosure` | YouTube requires creators to disclose realistic AI-generated or altered content, using the AI use setting (Yes or No) when uploading in YouTube Studio. | official | high | [YouTube Help, Disclosing use of altered or synthetic content](https://support.google.com/youtube/answer/14328491) |
| `instagram.paid_partnership` | Instagram's branded content policies require the paid partnership label to tag the featured brand. | official | high | [Instagram Help, paid partnership label for organic branded content](https://help.instagram.com/android-app/1109894795810258) |

Rows marked "no verified fact in the database" are good fact PRs. If you have a primary source, see `CONTRIBUTING.md`.
