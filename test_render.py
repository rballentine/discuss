"""One page.html serves every client, so a fix for one must not break another.

python -m unittest discover -p "test_*.py"   (from this folder)
"""
import json
import re
import tempfile
import unittest
from pathlib import Path

from render import main, problems, render_state

STATE = {"slug": "test", "title": "Test", "round": 1,
         "items": [{"n": 1, "title": "Point", "status": "open",
                    # A point the user wrote opens with their own text.
                    "thread": [{"who": "you", "round": 1, "text": "Their point, verbatim"},
                               {"who": "claude", "round": 1, "text": "Hi </script><b>x</b>",
                                "choices": [{"label": "Weekly", "reply": "Weekly, Mondays 06:00 ET"},
                                            {"label": "Nightly", "reply": "Nightly </script>, alert only on failure"}]}]}]}
DOCTYPE = '<!doctype html><html lang="en"><meta charset="utf-8">'


def embedded(page: str) -> dict:
    return json.loads(re.search(r'<script type="application/json" id="state">(.*?)</script>', page, re.S).group(1))


class RenderTests(unittest.TestCase):
    def test_every_client_embeds_the_state_and_fills_every_placeholder(self):
        for client in ("claude", "codex", "browser", "hosted"):
            with self.subTest(client=client):
                page = render_state(STATE, client)
                # Any placeholder, so a new one the renderer doesn't fill fails here.
                self.assertNotRegex(page, "__[A-Z]+__")
                self.assertEqual(embedded(page), {**STATE, "client": client})

    def test_each_client_keeps_its_own_delivery(self):
        claude, codex, browser = (render_state(STATE, c) for c in ("claude", "codex", "browser"))
        self.assertIn('window.claude.use("comments")', claude)
        self.assertIn("Send to Claude", claude)
        self.assertNotIn("Send to Claude", codex)
        self.assertIn("Send to Codex", codex)
        self.assertTrue(browser.startswith("<!doctype html>"))
        self.assertIn('<meta charset="utf-8">', browser)

    def test_a_malformed_state_is_refused(self):
        with self.assertRaises(ValueError):
            render_state({**STATE, "items": []})

    def test_problems_match_the_apps_twin(self):
        # A host app that renders pages itself refuses the same states in the same words; these are
        # the cases where Python alone would have let a state through or crashed.
        point = STATE["items"][0]
        cases = {
            "round: an integer from 1": {**STATE, "round": True},
            "items[0]: an object with n, title, status and thread": {**STATE, "items": ["a point"]},
            "items[0].n: a unique integer": {**STATE, "items": [{**point, "n": [1]}]},
            "items[0].status: one of ['done', 'dropped', 'open', 'parked']": {**STATE, "items": [{**point, "status": ["open"]}]},
            "items[0].outcome: required once a point is settled (it is the folded line)":
                {**STATE, "items": [{**point, "status": "done", "outcome": None}]},
            "items[0].thread[0]: needs who (claude|codex|you), round (int) and text":
                {**STATE, "items": [{**point, "thread": [{"who": "you", "round": 1, "text": None}]}]},
        }
        answer = point["thread"][1]
        choices = "items[0].thread[1].choices: at most 3, each a label (at most 24 characters) and a reply (at most 300)"
        for name, bad in {"four": answer["choices"] * 2, "not a list": {"label": "A", "reply": "B"},
                          "blank label": [{"label": " ", "reply": "B"}], "long label": [{"label": "x" * 25, "reply": "B"}],
                          "no reply": [{"label": "A"}], "long reply": [{"label": "A", "reply": "x" * 301}]}.items():
            with self.subTest(choices=name):
                self.assertEqual(problems({**STATE, "items": [{**point, "thread": [point["thread"][0], {**answer, "choices": bad}]}]}),
                                 [choices])
        # Python's len counts code points; the app's twin must count an emoji once too.
        self.assertEqual(problems({**STATE, "items": [{**point, "thread": [{**answer, "choices": [{"label": "\U0001F600" * 24, "reply": "B"}]}]}]}), [])
        for problem, state in cases.items():
            with self.subTest(problem=problem):
                self.assertEqual(problems(state), [problem])
        self.assertEqual(problems([]), ["state: a JSON object"])


class HostedRenderTests(unittest.TestCase):
    STATE = {"slug": "test", "title": "Test <b>title</b>", "round": 2,
             "items": [{"n": 1, "title": "First", "status": "open",
                        "thread": [{"who": "claude", "round": 1, "text": "Hello </script><script>alert(1)</script>"}]},
                       {"n": 2, "title": "Second", "status": "done", "outcome": "Agreed",
                        "thread": [{"who": "claude", "round": 2, "text": "Done"}]}]}

    def test_hosted_is_a_full_document_named_for_its_assistant(self):
        page = render_state(self.STATE, "hosted", "Helper")
        self.assertTrue(page.startswith(DOCTYPE))
        self.assertTrue(page.endswith("</html>"))
        self.assertIn("<title>Test &lt;b&gt;title&lt;/b&gt;</title>", page)
        self.assertIn("Send to Helper", page)
        self.assertNotIn("Send to Claude", page)
        state = embedded(page)
        self.assertEqual(state["client"], "hosted")
        self.assertEqual(state["items"], self.STATE["items"])
        # Reply text can't close the script that carries the state.
        self.assertEqual(page.count("</script>"), 2)

    def test_hosted_wraps_the_page_like_browser(self):
        browser, hosted = render_state(self.STATE, "browser"), render_state(self.STATE, "hosted")
        self.assertEqual(hosted.split("<title>", 1)[0], browser.split("<title>", 1)[0])
        self.assertIn("Send to Codex", browser)

    def test_bad_input_is_refused(self):
        with self.assertRaises(ValueError):
            render_state(self.STATE, "slack")
        with self.assertRaises(ValueError):
            render_state({**self.STATE, "round": 0}, "hosted")
        # The name lands in script strings too, so a quote or a tag is refused rather than escaped.
        for name in ("O'Brien", "<b>bot</b>", "", "x" * 33):
            with self.subTest(name=name), self.assertRaises(ValueError):
                render_state(self.STATE, "hosted", name)

    def test_command_line_accepts_hosted(self):
        with tempfile.TemporaryDirectory() as temp:
            src = Path(temp) / "state.json"
            src.write_text(json.dumps(self.STATE), encoding="utf-8")
            self.assertEqual(main(["render.py", str(src), "--client", "hosted", "--assistant", "Helper"]), 0)
            page = src.with_suffix(".html").read_text(encoding="utf-8")
            self.assertEqual(embedded(page)["client"], "hosted")
            self.assertIn("Send to Helper", page)


if __name__ == "__main__":
    unittest.main()
