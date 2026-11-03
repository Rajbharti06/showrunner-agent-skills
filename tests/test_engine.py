import json
import os
import re
import tempfile
import unittest
from datetime import date

from _paths import EXAMPLES  # noqa: F401  (also puts the engine on sys.path)

os.environ["SHOWRUNNER_HOME"] = tempfile.mkdtemp()
os.environ["SHOWRUNNER_TODAY"] = "2026-11-02"

from showrunner import (beats, calibrate, captions, clips, experiments, facts, hooks, humanize, ideas, intake,  # noqa: E402
                        outliers, planner, playbooks, retention, srt, store, titles, tools)
from showrunner.util import ToolError  # noqa: E402


def ex(name):
    with open(os.path.join(EXAMPLES, name), encoding="utf-8") as fh:
        return fh.read()


class TestHooks(unittest.TestCase):
    def test_specific_beats_generic(self):
        a = hooks.score_hook("I sat in on 41 interviews. 33 candidates failed the same way.")
        b = hooks.score_hook("Here are some tips for your next interview")
        self.assertGreater(a["score"], b["score"])

    def test_dealbreakers_cap_score(self):
        r = hooks.score_hook("Hey guys, welcome back to my channel")
        self.assertLessEqual(r["score"], 35)
        self.assertTrue(r["dealbreakers"])

    def test_hindi_and_hinglish_do_not_crash(self):
        r = hooks.score_hook("Maine 41 interviews dekhe aur 33 log ek hi galti karte hain")
        self.assertGreaterEqual(r["components"]["specificity"], 50)
        hooks.score_hook("मैंने 41 इंटरव्यू देखे")

    def test_empty_hook_raises(self):
        with self.assertRaises(ValueError):
            hooks.score_hook("   ")

    def test_weights_sum_to_one(self):
        w = hooks.load_weights()
        self.assertAlmostEqual(sum(w[k] for k in hooks.COMPONENTS), 1.0, places=3)


class TestTitlesBeatsCaptions(unittest.TestCase):
    def test_shouty_title_is_weak(self):
        self.assertLess(titles.score_title("You WON'T BELIEVE This Interview Hack!!!")["score"], 45)

    def test_over_100_chars_flagged(self):
        r = titles.score_title("x" * 120)
        self.assertTrue(any("100" in f for f in r["flags"]))

    def test_pair_overlap(self):
        self.assertLess(titles.pair_check("How I Got 3 Job Offers", "3 JOB OFFERS")["score"], 50)
        self.assertGreater(titles.pair_check("How I Got 3 Job Offers", "NO REFERRAL")["score"], 80)

    def test_beats_split_sentences(self):
        r = beats.beat_sheet("Stop doing this. Do that instead. It works because of reasons and also more reasons here.")
        self.assertEqual(len(r["beats"]), 3)

    def test_caption_hashtag_cap_and_link(self):
        r = captions.lint("Hello 3 people #a #b #c #d #e #f https://x.co", "instagram")
        names = {c["name"]: c["level"] for c in r["checks"]}
        self.assertEqual(names["HASHTAGS"], "FAIL")
        self.assertEqual(names["LINKS"], "WARN")

    def test_caption_unknown_platform(self):
        with self.assertRaises(ValueError):
            captions.lint("x", "myspace")


class TestHumanize(unittest.TestCase):
    def test_em_dash_gone_and_urls_untouched(self):
        r = humanize.humanize("See https://example.com/a--b — it works — really.")
        self.assertNotIn("—", r["text"])
        self.assertIn("https://example.com/a--b", r["text"])

    def test_invisible_chars_removed(self):
        r = humanize.humanize("Hello​ world⁠ again.")
        self.assertEqual(r["text"], "Hello world again.")

    def test_stock_phrases_cut(self):
        r = humanize.humanize("In conclusion, we delve into a rich tapestry of ideas.")
        self.assertNotIn("delve", r["text"].lower())
        self.assertNotIn("tapestry", r["text"].lower())

    def test_ordinary_text_is_not_shouting(self):
        r = humanize.humanize("This is a perfectly ordinary sentence with plenty of words in it.")
        self.assertFalse(any("shouted" in t["msg"] for t in r["needs_rewrite"]))

    def test_real_shouting_is_flagged(self):
        self.assertTrue(any("shouted" in t["msg"] for t in humanize.structural_tells("THIS IS SO BAD RIGHT NOW")))

    def test_hindi_survives(self):
        text = "यह एक टेस्ट है। यह दूसरा वाक्य है।"
        self.assertEqual(humanize.humanize(text)["text"], text)

    def test_detect_ranks_slop_below_plain(self):
        slop = humanize.detect("In today's fast-paced world, we delve into a rich tapestry. It's not just X, it's Y.")["human_score"]
        plain = humanize.detect("I ran 3 mock interviews with Priya last week. She froze on the first question. We fixed it in 20 minutes.")["human_score"]
        self.assertGreater(plain, slop)


class TestStudyTools(unittest.TestCase):
    def test_outliers_use_own_account_median(self):
        r = outliers.rank(ex("outliers.csv"), "short", 5)
        self.assertEqual(len(r["items"]), 30)
        top = r["top"][0] if r["top"] else r["items"][0]
        self.assertGreater(top["multiple"], 10)
        self.assertEqual(top["account"], "@acct_a")

    def test_retention_front_loaded_no_duplicate_bumps(self):
        r = retention.analyze(ex("retention.csv"))
        self.assertEqual(r["shape"], "front-loaded cliff")
        starts = [b["start"] for b in r["bumps"]]
        self.assertEqual(len(starts), len(set(starts)))
        self.assertTrue(all(c["start"] < 0.92 * r["duration"] for c in r["cliffs"]))

    def test_srt_roundtrip_and_stats(self):
        res = srt.analyze(ex("talk.srt"))
        self.assertEqual(res["cues"], 60)
        self.assertTrue(150 < res["wpm"] < 185)
        self.assertTrue(res["cuts"])

    def test_rechunk_has_no_orphans_or_overlaps(self):
        out = srt.parse(srt.rechunk(ex("talk.srt")))
        self.assertGreater(len(out), 80)
        self.assertEqual(sum(1 for c in out if len(c["text"].split()) == 1), 0)
        self.assertTrue(all(len(c["text"]) <= 28 for c in out))
        for a, b in zip(out, out[1:]):
            self.assertLessEqual(a["end"], b["start"] + 1e-6)

    def test_clips_command_and_rebased_captions(self):
        r = clips.find(ex("talk.srt"), n=3, source="my video.mp4")
        self.assertEqual(len(r["clips"]), 3)
        c = r["clips"][0]
        self.assertIn('-i "my video.mp4"', c["ffmpeg"])
        self.assertIn("crop=ih*9/16:ih", c["ffmpeg"])
        self.assertTrue(c["captions_srt"].startswith("1\n00:00:00,000"))
        self.assertTrue(20 <= c["dur"] <= 60)

    def test_vtt_input(self):
        vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nHello there friend\n\n00:00:03.500 --> 00:00:05.000\nThis is <b>bold</b>\n"
        cues = srt.parse(vtt)
        self.assertEqual(len(cues), 2)
        self.assertEqual(cues[1]["text"], "This is bold")

    def test_bad_inputs_raise_toolerror(self):
        with self.assertRaises(ToolError):
            srt.parse("nothing here")
        with self.assertRaises(ToolError):
            outliers.rank("a,b\n1,2")
        with self.assertRaises(ToolError):
            calibrate.run("account,views,hook\na,1,x")


class TestPlanning(unittest.TestCase):
    def test_spokes_survive_a_tight_week(self):
        cap = planner.capacity(6, "seed", "instagram", ["tiktok", "youtube"], "mix")
        plats = {i["platform"] for i in cap["items"]}
        self.assertIn("tiktok", plats)
        self.assertLessEqual(cap["planned_min"], cap["creation_budget_min"])

    def test_never_plans_more_than_the_budget(self):
        for hrs in (1, 2, 3, 5, 8, 15, 30):
            for stage in planner.STAGES:
                cap = planner.capacity(hrs, stage, "youtube", ["instagram", "linkedin"], "mix")
                self.assertLessEqual(cap["planned_min"], max(cap["creation_budget_min"], 1) + 360, (hrs, stage))

    def test_same_day_posts_get_different_times(self):
        plan = planner.build("instagram", ["tiktok"], 10, "growing", "mix", 2)
        seen = set()
        for r in plan["rows"]:
            key = (r["date"], r["platform"], r["time"])
            self.assertNotIn(key, seen)
            seen.add(key)

    def test_start_is_a_monday(self):
        plan = planner.build("instagram", [], 5, "zero", "mix", 1, start=date(2026, 11, 4))
        self.assertEqual(date.fromisoformat(plan["start"]).weekday(), 0)

    def test_ics_escapes_and_folds(self):
        plan = planner.build("instagram", [], 5, "zero", "mix", 1, pillars=["Prep, interviews; etc"])
        ics = planner.to_ics(plan)
        self.assertIn(r"\,", ics)
        self.assertIn(r"\;", ics)
        self.assertTrue(ics.startswith("BEGIN:VCALENDAR\r\n"))
        self.assertTrue(re.search(r"DTSTAMP:\d{8}T\d{6}Z", ics))
        self.assertTrue(all(len(l.encode()) <= 75 for l in ics.split("\r\n")))

    def test_multiple_content_types(self):
        cap = planner.capacity(10, "seed", "linkedin", ["x"], ["long_video", "text"])
        fmts = {(i["platform"], i["format"]) for i in cap["items"]}
        self.assertIn(("linkedin", "text_post"), fmts)

    def test_unknown_platform(self):
        with self.assertRaises(ToolError):
            planner.capacity(5, "zero", "myspace", [])


class TestIntake(unittest.TestCase):
    def test_goal_changes_the_hub(self):
        a = intake.recommend({"content_types": ["text"], "audience": "B2B SaaS founders", "goal": "leads", "stage": "seed", "hours_per_week": 6})
        b = intake.recommend({"content_types": ["short_video"], "audience": "college students", "goal": "audience", "stage": "seed", "hours_per_week": 6})
        self.assertEqual(a["hub"], "linkedin")
        self.assertIn(b["hub"], ("tiktok", "instagram", "youtube"))
        self.assertNotEqual(a["hub"], b["hub"])

    def test_named_platforms_are_respected_but_capped_by_hours(self):
        r = intake.recommend({"content_types": ["short_video"], "audience": "x", "goal": "audience", "stage": "zero", "hours_per_week": 2,
                              "platforms": ["instagram", "tiktok", "youtube", "x"]})
        self.assertLessEqual(len(r["spokes"]), 1)
        self.assertTrue(any("platforms" in n for n in r["notes"]))

    def test_always_says_it_is_a_hypothesis(self):
        r = intake.recommend({"content_types": ["mix"], "goal": "income", "stage": "zero", "hours_per_week": 5})
        self.assertIn("not a prediction", r["disclaimer"])

    def test_bad_stage(self):
        with self.assertRaises(ToolError):
            intake.recommend({"stage": "huge"})


class TestHonesty(unittest.TestCase):
    def test_calibrate_refuses_to_write_weights_under_30(self):
        res = calibrate.run("account,views,hook\n" + "\n".join("a,%d,hook %d here" % (100 + i * 50, i) for i in range(12)), write_weights=True)
        self.assertIsNone(res["wrote"])
        self.assertFalse(os.path.exists(store.weights_path()))

    def test_calibrate_example(self):
        res = calibrate.run(ex("posts.csv"))
        self.assertEqual(res["posts_used"], 36)
        for k in hooks.COMPONENTS:
            self.assertLessEqual(res["report"][k]["low"], res["report"][k]["auc"])
            self.assertLessEqual(res["report"][k]["auc"], res["report"][k]["high"])

    def test_experiment_small_sample_is_not_a_verdict(self):
        experiments.create("h", "v", "views")
        for v in (100, 120):
            experiments.log("exp-001", "A", v)
        for v in (900, 950):
            experiments.log("exp-001", "B", v)
        self.assertIn("Not enough", experiments.review("exp-001")[0]["verdict"])

    def test_experiment_noise_is_not_a_win(self):
        self.assertGreater(experiments._perm_p([10, 20, 30, 40, 50], [15, 25, 35, 45, 55]), 0.5)
        self.assertLess(experiments._perm_p([1, 2, 3, 4, 5], [100, 200, 300, 400, 500]), 0.05)

    def test_facts_database_is_well_formed(self):
        self.assertEqual(facts.check(), [])

    def test_every_fact_has_a_status_and_date(self):
        for f in facts.all_facts():
            self.assertIn(f["status"], facts.STATUS)
            date.fromisoformat(f["as_of"])

    def test_stale_facts_flagged_after_window(self):
        self.assertEqual(facts.stale(now=date(2026, 11, 3)), [])
        self.assertTrue(facts.stale(now=date(2027, 6, 1)))

    def test_ideas_flag_duplicates_and_unrated(self):
        r = ideas.score("The first two minutes of a system design interview | 5 | 5 | 4 | 5 | 2\nThe first two minutes of a design interview\n")
        self.assertTrue(r["duplicates"])
        self.assertTrue(any("no ratings" in n for n in r["notes"]))


class TestPlaybooksAndTools(unittest.TestCase):
    def test_every_playbook_step_names_a_known_gate_and_skill(self):
        gates = set(playbooks.GATE_HELP)
        for row in playbooks.list_all():
            pb = playbooks.get(row["id"])
            ids = [s["id"] for s in pb["steps"]]
            self.assertEqual(len(ids), len(set(ids)), pb["id"])
            for s in pb["steps"]:
                self.assertIn(s["gate"], gates)
                self.assertTrue(s["skill"] == "showrunner" or s["skill"].startswith("sr-"), s["skill"])

    def test_run_state_survives_and_gates_are_visible(self):
        run = playbooks.start("profile-makeover", "t1")
        n = playbooks.next_step(run["id"])
        self.assertEqual(n["step"]["id"], "audit")
        n = playbooks.done("audit", "scored 41/100", run["id"])
        self.assertEqual(n["step"]["id"], "line")
        self.assertEqual(n["earlier_notes"]["audit"], "scored 41/100")
        with self.assertRaises(ToolError):
            playbooks.done("nope", "", run["id"])

    def test_unknown_playbook(self):
        with self.assertRaises(ToolError):
            playbooks.get("nope")

    def test_coercion(self):
        r = tools.run("calendar_build", {"hub": "instagram", "hours_per_week": "6", "weeks": "1", "stage": "zero"})
        self.assertTrue(r["ok"], r)
        r = tools.run("calendar_build", {"hub": "instagram", "weeks": "one"})
        self.assertFalse(r["ok"])
        self.assertIn("whole number", r["error"])
        r = tools.run("hook_score", {"text": "x", "platform": "radio"})
        self.assertIn("must be one of", r["error"])

    def test_every_tool_has_schema_description_and_unique_cli(self):
        clis = [t.cli for t in tools.TOOLS]
        self.assertEqual(len(clis), len(set(clis)))
        for t in tools.TOOLS:
            self.assertTrue(len(t.description) > 40, t.name)
            sch = t.schema(allow_files=False)
            json.dumps(sch)
            self.assertNotIn("file", sch["properties"])

    def test_profile_roundtrip_and_validation(self):
        with self.assertRaises(ToolError):
            store.save_profile({"stage": "huge"})
        p = store.save_profile({"niche": "n", "stage": "seed", "hours_per_week": 4})
        self.assertEqual(store.load_profile()["niche"], "n")
        self.assertIn("updated", p)

    def test_text_over_limit_is_refused(self):
        r = tools.run("text_detect", {"text": "a" * (tools.MAX_INPUT_CHARS + 1)})
        self.assertFalse(r["ok"])


class TestFoundInALiveSession(unittest.TestCase):
    """Bugs found by running the plugin in a real Claude Code session (Windows, November 2026)."""

    def test_boolean_flags_take_yes_and_no(self):
        from showrunner import cli
        ap = cli._build_parser()
        self.assertIs(ap.parse_args(["intake", "--on-camera", "no"]).on_camera, False)
        self.assertIs(ap.parse_args(["intake", "--on-camera=yes"]).on_camera, True)
        self.assertIs(ap.parse_args(["intake", "--no-on-camera"]).on_camera, False)
        self.assertIs(ap.parse_args(["intake", "--on-camera"]).on_camera, True)
        self.assertIsNone(ap.parse_args(["intake"]).on_camera)
        a = ap.parse_args(["playbook", "done", "--skip", "voice"])
        self.assertEqual((a.step, a.skip), ("voice", True))

    def test_not_on_camera_reaches_the_plan(self):
        r = tools.run("intake_recommend", {"content_types": ["short_video"], "goal": "income", "stage": "zero",
                                           "hours_per_week": 5, "on_camera": False})
        self.assertTrue(r["ok"], r)
        self.assertIs(r["data"]["inputs"]["on_camera"], False)
        self.assertIn("faceless", " ".join(r["data"]["notes"]))

    def test_profile_save_takes_the_intake_flags(self):
        r = tools.run("profile_save", {"content_types": ["short_video"], "audience": "hostel students", "goal": "income",
                                       "stage": "zero", "hours_per_week": 5, "hub": "youtube", "on_camera": False})
        self.assertTrue(r["ok"], r)
        prof = store.load_profile()
        self.assertEqual(prof["content_type"], "short_video")
        self.assertEqual(prof["audience"]["who"], "hostel students")
        self.assertIs(prof["on_camera"], False)
        self.assertFalse(tools.run("profile_save", {})["ok"])

    def test_profile_accepts_content_type_as_a_list(self):
        self.assertEqual(store.save_profile({"content_type": ["carousel"]})["content_type"], "carousel")
        self.assertEqual(store.save_profile({"content_type": ["short_video", "carousel"]})["content_type"], "mix")

    def test_playbook_show_names_step_ids_and_next_says_how_to_skip(self):
        shown = playbooks.render_show(playbooks.get("zero-to-first-1000"))
        for sid in ("intake", "positioning", "voice", "research"):
            self.assertRegex(shown, r"\d\. %s\s" % sid)
        run = playbooks.start("profile-makeover", "skip-hint")
        self.assertIn("playbook done audit --skip", playbooks.render_next(playbooks.next_step(run["id"])))

    def test_install_hint_is_quoted_and_names_an_installed_skill(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("install", os.path.join(os.path.dirname(EXAMPLES), "install.py"))
        install = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(install)
        cmd = install.check_command(os.path.join("C:", "Users", "Jane Doe", ".claude", "skills"), ["sr-hook", "sr-script"])
        self.assertTrue(cmd.startswith('python "') and cmd.endswith('" doctor'), cmd)
        self.assertIn("sr-hook", cmd)
        self.assertIn("showrunner", install.check_command("x", ["sr-hook", "showrunner"]))


class TestRepoHealth(unittest.TestCase):
    """Things that kept going wrong while the repo was written: lookups, wording, and drift."""

    def test_facts_lookup_by_id_and_prefix(self):
        self.assertEqual([f["id"] for f in facts.query(fid="youtube.hashtags.cap")], ["youtube.hashtags.cap"])
        self.assertGreaterEqual(len(facts.query(fid="x.")), 2)
        self.assertEqual(facts.query(fid="nope.nothing"), [])
        r = tools.run("facts_search", {"id": "general.ftc_disclosure"}, allow_files=False)
        self.assertIn("material connection", r["text"])

    def test_official_policy_facts_link_to_the_platform(self):
        for fid in ("general.ftc_disclosure", "youtube.ai_disclosure", "instagram.paid_partnership"):
            f = facts.get(fid)
            self.assertTrue(f["url"], fid)

    def test_profile_accepts_a_lessons_list(self):
        self.assertEqual(store.validate_profile({"lessons": ["numbers in the first line helped (n=5 each)"]}), [])
        self.assertTrue(store.validate_profile({"lessons": "not a list"}))

    def test_caption_link_warning_reads_correctly_on_every_platform(self):
        for platform in ("instagram", "tiktok"):
            res = captions.lint("Read this https://example.com now", platform)
            text = " ".join(str(c) for c in res["checks"])
            self.assertNotIn("a an ", text)
            self.assertIn("not clickable", text)

    def test_every_playbook_step_uses_a_real_skill(self):
        skills = set(os.listdir(os.path.join(os.path.dirname(EXAMPLES), "skills")))
        for pb in playbooks.list_all():
            full = playbooks.get(pb["id"])
            for step in full["steps"]:
                self.assertIn(step["skill"], skills, "%s / %s" % (pb["id"], step["id"]))

    def test_adapted_pieces_keep_the_pillar_of_their_source(self):
        res = planner.build("tiktok", ["youtube"], 5, "zero", "short_video", weeks=2,
                                     start=date(2026, 11, 9), pillars=["interviews", "projects", "tools"])
        last_make = None
        for r in res["rows"]:
            if r["task"].startswith("Make"):
                last_make = r
            else:
                self.assertEqual(r["pillar"], last_make["pillar"], r)

    def test_fact_check_rejects_unsourced_reports(self):
        base = dict(facts.get("youtube.hashtags.cap"))
        good = dict(base, id="t.good", status="reported", url="https://example.com/x")
        no_url = dict(base, id="t.nourl", status="reported", url=None)
        study = dict(base, id="t.study", status="study", url=None)
        infer = dict(base, id="t.infer", status="inferred", url=None, note="")
        real = facts.all_facts
        facts.all_facts = lambda: [good, no_url, study, infer]
        try:
            problems = " ".join(facts.check())
        finally:
            facts.all_facts = real
        self.assertNotIn("t.good", problems)
        self.assertIn("t.nourl", problems)
        self.assertIn("t.study", problems)
        self.assertIn("t.infer", problems)

    def test_versions_agree(self):
        import re
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        import showrunner
        pyproject = open(os.path.join(root, "pyproject.toml"), encoding="utf-8").read()
        m = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.M)
        self.assertEqual(m.group(1), showrunner.__version__)
        for rel in (".claude-plugin/plugin.json",):
            data = json.load(open(os.path.join(root, rel), encoding="utf-8"))
            self.assertEqual(data["version"], showrunner.__version__, rel)
        for rel in (".claude-plugin/marketplace.json", ".github/ISSUE_TEMPLATE/config.yml"):
            self.assertTrue(os.path.exists(os.path.join(root, rel)), rel)

    def test_repo_scripts_pass(self):
        import subprocess
        import sys
        root = os.path.dirname(EXAMPLES)
        for script, args in (("validate_skills.py", ["--quiet"]), ("lint_prose.py", []),
                             ("sync_shims.py", ["--check"]), ("gen_refs.py", ["--check"])):
            r = subprocess.run([sys.executable, os.path.join(root, "scripts", script)] + args,
                               capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=root)
            self.assertEqual(r.returncode, 0, "%s failed:\n%s%s" % (script, r.stdout, r.stderr))


if __name__ == "__main__":
    unittest.main()
