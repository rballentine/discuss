"""Serve one discussion on loopback and queue browser replies into its Codex chat.

python serve.py STATE.json --thread UUID [--port 0]
Keep this temporary development server running while the discussion is in use.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from render import render_state

MAX_BODY = 256 * 1024
MAX_IMAGE = 1024 * 1024  # The page shrinks anything larger before sending it.
MAX_DRAIN = 16 * 1024 * 1024  # The most of a refused request read so its sender still gets the answer.
IMAGE_TYPES = {"image/png": "png", "image/jpeg": "jpg", "image/gif": "gif", "image/webp": "webp"}
IMAGE_PATH = re.compile(r"^/images/([0-9a-f-]{36}\.(png|jpg|gif|webp))$")


def write_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


class DiscussionServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, state_path: Path, thread: str, port: int, codex: str):
        self.state_path = state_path.resolve()
        self.thread = str(uuid.UUID(thread))
        self.codex = codex
        self.submissions = self.state_path.parent / (self.state_path.stem + "-replies")
        self.submissions.mkdir(exist_ok=True)
        self.images = self.state_path.parent / (self.state_path.stem + "-images")
        self.images.mkdir(exist_ok=True)
        self.submit_lock = threading.Lock()
        super().__init__(("127.0.0.1", port), Handler)
        self.origin = f"http://127.0.0.1:{self.server_port}"

    def state(self) -> dict:
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def submit(self, body: dict) -> tuple[int, dict]:
        submission_id = str(uuid.UUID(body["id"]))
        text, round_number = body["text"], body["round"]
        state = self.state()
        if not isinstance(text, str) or not text.strip() or len(text.encode("utf-8")) > MAX_BODY // 2:
            raise ValueError("Reply text is empty or too large")
        if type(round_number) is not int or not 1 <= round_number <= state["round"]:
            raise ValueError("Invalid discussion round")
        path = self.submissions / (submission_id + ".json")
        with self.submit_lock:
            if path.exists():
                prior = json.loads(path.read_text(encoding="utf-8"))
                if prior["text"] != text or prior["round"] != round_number:
                    return 409, {"error": "This submission ID already belongs to different replies"}
                if prior["delivery"] == "queued":
                    return 200, {"queued": True}
                return 409, {"error": "Delivery is uncertain. Check this Codex chat before retrying or copying these replies"}
            record = {"id": submission_id, "slug": state["slug"], "round": round_number,
                      "text": text, "delivery": "sending", "thread": self.thread,
                      "state": str(self.state_path)}
            write_json(path, record)
            # Keep arbitrarily long reply text out of Windows' command-line length limit.
            # One readable link in chat; the receipt carries the state path and full replies.
            prompt = f"[/discuss · replies to round {round_number}](<{path.as_posix()}>)"
            try:
                result = subprocess.run(
                    # From the server's own directory (the project it was started in), wherever the skill is installed.
                    [self.codex, "queue", "--thread", self.thread, "--message", prompt],
                    capture_output=True,
                    text=True, encoding="utf-8", errors="replace", timeout=30,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                queued = result.returncode == 0 and f"for thread {self.thread}" in result.stdout
            except (OSError, subprocess.TimeoutExpired):
                queued = False
            record["delivery"] = "queued" if queued else "unknown"
            write_json(path, record)
            if not queued:
                return 502, {"error": "Codex did not confirm queueing. Check the chat before retrying; your replies are saved"}
            return 200, {"queued": True}


class Handler(BaseHTTPRequestHandler):
    server: DiscussionServer

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, *_):
        pass  # Never log discussion text or arbitrary request paths.

    def respond(self, status: int, value, content_type="application/json; charset=utf-8"):
        content = value if isinstance(value, bytes) else value.encode("utf-8") if isinstance(value, str) else json.dumps(value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(content)

    def refuse_size(self, size: int, message: str):
        """Takes what is being sent before answering: closing on unread data resets the socket, and the sender loses the answer."""
        left = min(size, MAX_DRAIN)
        while left > 0:
            chunk = self.rfile.read(min(left, 64 * 1024))
            if not chunk:
                break
            left -= len(chunk)
        return self.respond(413, {"error": message})

    def valid_host(self):
        return self.headers.get("Host") == self.server.origin.removeprefix("http://")

    def do_GET(self):
        if not self.valid_host():
            return self.respond(403, {"error": "Invalid host"})
        try:
            state = self.server.state()
            if self.path == "/":
                return self.respond(200, render_state(state, "browser"), "text/html; charset=utf-8")
            if self.path == "/version":
                return self.respond(200, {"round": state["round"]})
            image = IMAGE_PATH.match(self.path)
            if image and (self.server.images / image[1]).is_file():
                kind = "jpeg" if image[2] == "jpg" else image[2]
                return self.respond(200, (self.server.images / image[1]).read_bytes(), "image/" + kind)
            self.respond(404, {"error": "Not found"})
        except (ValueError, OSError):
            self.respond(503, {"error": "Discussion state is being updated; try again"})

    def do_POST(self):
        if (not self.valid_host() or self.headers.get("Origin") != self.server.origin
                or self.headers.get("X-Discuss-Client") != "browser"):
            return self.respond(403, {"error": "Only this discussion page can submit replies"})
        if self.path == "/images":
            return self.save_image()
        if self.path != "/replies":
            return self.respond(404, {"error": "Not found"})
        if self.headers.get("Content-Type") != "application/json":
            return self.respond(415, {"error": "Expected JSON"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= MAX_BODY:
                return self.refuse_size(size, "Replies exceed the 256 KiB request limit")
            body = json.loads(self.rfile.read(size))
            status, response = self.server.submit(body)
            self.respond(status, response)
        except (ValueError, KeyError, TypeError):
            self.respond(400, {"error": "Invalid reply submission"})
        except OSError:
            self.respond(500, {"error": "Could not save replies; check the chat before retrying"})

    def save_image(self):
        kind = IMAGE_TYPES.get(self.headers.get("Content-Type"))
        if not kind:
            return self.respond(415, {"error": "Expected a PNG, JPEG, GIF or WebP image"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= MAX_IMAGE:
                return self.refuse_size(size, "Images can be at most 1 MiB")
            name = f"{uuid.uuid4()}.{kind}"
            (self.server.images / name).write_bytes(self.rfile.read(size))
            self.respond(200, {"path": "/images/" + name})
        except ValueError:
            self.respond(400, {"error": "Invalid image"})
        except OSError:
            self.respond(500, {"error": "Could not save that image"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state", type=Path)
    parser.add_argument("--thread", required=True)
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    codex = shutil.which("codex")
    if not codex:
        parser.error("codex CLI is not on PATH")
    with DiscussionServer(args.state, args.thread, args.port, codex) as server:
        state = server.state()
        render_state(state, "browser")  # Validate before advertising the page.
        state["browser_url"] = server.origin + "/"
        state["thread_id"] = server.thread
        write_json(args.state, state)
        print(server.origin + "/", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
