# Knowledge files for a Custom GPT

A Custom GPT accepts up to 20 knowledge files. Upload these, in this order of importance.

1. `dist/showrunner-all-skills.zip` (run `python scripts/build_dist.py` to make it). Needed only if you turn on Code Interpreter so the model can run the scoring tools. It contains every skill and the engine.
2. `skills/showrunner/SKILL.md`
3. `skills/showrunner/references/playbooks.md`
4. `skills/sr-intake/SKILL.md`
5. `skills/sr-strategy/SKILL.md`
6. `skills/sr-hook/SKILL.md`
7. `skills/sr-hook/references/hook-shapes.md`
8. `skills/sr-script/SKILL.md`
9. `skills/sr-caption/SKILL.md`
10. `skills/sr-humanize/SKILL.md`
11. `skills/sr-policy-check/SKILL.md`
12. `skills/sr-policy-check/references/checklist.md`
13. `skills/sr-calendar/SKILL.md`
14. `skills/sr-growth-loop/SKILL.md`
15. `skills/sr-audit/SKILL.md`
16. `skills/sr-platform-guide/references/youtube.md`
17. `skills/sr-platform-guide/references/instagram.md`
18. `skills/sr-platform-guide/references/tiktok.md`
19. `skills/sr-platform-guide/references/linkedin.md`
20. `skills/sr-platform-guide/references/x-threads.md`

Leave out the `facebook.md` reference and the less-used skills if you hit the limit, and add them back as you need them. Or skip the list and upload `showrunner-all-skills.zip` alone with Code Interpreter on: the model can read the skills from inside it.

The instructions go in the Instructions box: [instructions.md](instructions.md).

Suggested name: Showrunner. Suggested conversation starters:

- I want to start posting but I do not know where
- Score and improve these hooks
- Turn my long video transcript into short clips
- Build me a four week plan that fits five hours a week
- Is this post okay to publish?
