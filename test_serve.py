"""Local transport checks; never calls a real Codex session.

python -m unittest discover -p test_serve.py   (from this folder)
"""
import http.client
import json
import subprocess
import tempfile
import threading
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from serve import DiscussionServer


class BrowserTransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "test.json"
        self.path.write_text(json.dumps({"slug": "test", "title": "Test", "round": 1,
            "items": [{"n": 1, "title": "Test", "status": "open",
                       "thread": [{"who": "codex", "round": 1, "text": "Hello"}]}]}), encoding="utf-8")
        self.server = DiscussionServer(self.path, str(uuid.uuid4()), 0, "codex.exe")
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.body = {"id": str(uuid.uuid4()), "round": 1, "text": "#1: test"}

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join()
        self.temp.cleanup()

    def request(self, method, path, body=None, **headers):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        connection.request(method, path, body, headers)
        response = connection.getresponse()
        result = response.status, response.read()
        connection.close()
        return result

    def test_only_page_and_version_are_readable(self):
        self.assertEqual(self.request("GET", "/")[0], 200)
        self.assertEqual(self.request("GET", "/version")[0], 200)
        self.assertEqual(self.request("GET", "/test.json")[0], 404)
        self.assertEqual(self.request("GET", "/", Host="evil.example")[0], 403)

    @patch("serve.subprocess.run")
    def test_cross_origin_cannot_queue(self, run):
        status, _ = self.request("POST", "/replies", json.dumps(self.body),
            **{"Origin": "https://evil.example", "Content-Type": "application/json", "X-Discuss-Client": "browser"})
        self.assertEqual(status, 403)
        run.assert_not_called()

    @patch("serve.subprocess.run")
    def test_queue_once_and_bind_id_to_content(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, f"Queued message x for thread {self.server.thread}.", "")
        self.assertEqual(self.server.submit(self.body)[0], 200)
        self.assertEqual(self.server.submit(self.body)[0], 200)
        self.assertEqual(self.server.submit({**self.body, "text": "changed"})[0], 409)
        self.assertEqual(run.call_count, 1)
        self.assertFalse(run.call_args.kwargs.get("shell", False))

    @patch("serve.subprocess.run", side_effect=subprocess.TimeoutExpired("codex", 30))
    def test_unknown_delivery_is_not_retried(self, run):
        self.assertEqual(self.server.submit(self.body)[0], 502)
        self.assertEqual(self.server.submit(self.body)[0], 409)
        self.assertEqual(run.call_count, 1)

    @patch("serve.subprocess.run")
    def test_long_replies_stored_outside_command_line(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, f"Queued message x for thread {self.server.thread}.", "")
        long_body = {**self.body, "text": "reply " * 10000}
        self.assertEqual(self.server.submit(long_body)[0], 200)
        command = run.call_args.args[0]
        self.assertLess(len(command[-1]), 2000)
        saved = json.loads((self.server.submissions / (self.body["id"] + ".json")).read_text(encoding="utf-8"))
        self.assertEqual(saved["text"], long_body["text"])
        # The compact chat link must still resolve all information needed to answer.
        target = Path(command[-1].split("](<", 1)[1][:-2])
        receipt = json.loads(target.read_text(encoding="utf-8"))
        state = json.loads(Path(receipt["state"]).read_text(encoding="utf-8"))
        self.assertEqual(receipt["id"], self.body["id"])
        self.assertEqual(receipt["text"], long_body["text"])
        self.assertEqual(state["slug"], receipt["slug"])
        self.assertNotIn("\n", command[-1])


if __name__ == "__main__":
    unittest.main()
