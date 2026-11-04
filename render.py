"""Render a /discuss state file into the page that shows it.

    python render.py STATE.json [OUT.html] [--client claude|codex|browser|hosted] [--assistant NAME]

OUT defaults to STATE with an .html suffix. The page is page.html beside this script with the
state embedded as JSON; the page draws everything from that JSON, so a round only changes the state.
`browser` (serve.py) and `hosted` (a host web app's sandboxed iframe) get a full HTML document.
--assistant names whoever answers the page; each client has a default.

A host app may render `hosted` pages itself from this page.html instead of running this script. If it
does, it should make the same substitutions and refuse the states problems() refuses, in the same words.
"""
from __future__ import annotations

import html
import argparse
import json
import re
import sys
from pathlib import Path

STATUSES = {"open", "done", "parked", "dropped"}
# The name the page gives the assistant that answers it, per client, unless the caller names one.
ASSISTANT = {"claude": "Claude", "codex": "Codex", "browser": "Codex", "hosted": "Claude"}
SLUG = re.compile(r"^[a-z0-9-]{1,24}$")
NAME = re.compile(r"^[A-Za-z0-9 ._-]{1,32}\Z")
# An answer's choice buttons: few enough to scan, a label that fits a button, a reply that reads on hover.
MAX_CHOICES, MAX_LABEL, MAX_REPLY = 3, 24, 300


def _text(value) -> str:
    """A value as text; missing or null is empty (str(None) would pass as "None")."""
    return "" if value is None else str(value)


def _int(value) -> bool:
    """A JSON integer. Python counts True as one; JSON and the page don't."""
    return isinstance(value, int) and not isinstance(value, bool)


def _choices(value) -> bool:
    """At most MAX_CHOICES {label, reply} objects, each label and reply non-blank and within its length."""
    return isinstance(value, list) and len(value) <= MAX_CHOICES and all(
        isinstance(c, dict)
        and isinstance(c.get("label"), str) and c["label"].strip() and len(c["label"]) <= MAX_LABEL
        and isinstance(c.get("reply"), str) and c["reply"].strip() and len(c["reply"]) <= MAX_REPLY
        for c in value)


def problems(state: dict) -> list[str]:
    if not isinstance(state, dict):
        return ["state: a JSON object"]
    out = []
    if not isinstance(state.get("slug"), str) or not SLUG.match(state["slug"]):
        out.append("slug: 1-24 characters of a-z, 0-9 and '-' (it names the files and the drafts' storage key)")
    if not isinstance(state.get("title"), str) or not state["title"].strip():
        out.append("title: required")
    if not _int(state.get("round")) or state["round"] < 1:
        out.append("round: an integer from 1")
    items = state.get("items")
    if not isinstance(items, list) or not items:
        return out + ["items: a non-empty list"]
    seen = set()
    for i, it in enumerate(items):
        where = f"items[{i}]"
        if not isinstance(it, dict):
            out.append(f"{where}: an object with n, title, status and thread")
            continue
        n = it.get("n")
        if not _int(n) or n in seen:
            out.append(f"{where}.n: a unique integer")
        else:
            seen.add(n)
        if not isinstance(it.get("title"), str) or not it["title"].strip():
            out.append(f"{where}.title: required")
        if not isinstance(it.get("status"), str) or it["status"] not in STATUSES:
            out.append(f"{where}.status: one of {sorted(STATUSES)}")
        elif it["status"] != "open" and not _text(it.get("outcome")).strip():
            out.append(f"{where}.outcome: required once a point is settled (it is the folded line)")
        thread = it.get("thread")
        if not isinstance(thread, list) or not thread:
            out.append(f"{where}.thread: a non-empty list")
            continue
        for j, e in enumerate(thread):
            if not isinstance(e, dict) or e.get("who") not in ("claude", "codex", "you") or not _int(e.get("round")) \
                    or not _text(e.get("text")).strip():
                out.append(f"{where}.thread[{j}]: needs who (claude|codex|you), round (int) and text")
            elif e.get("choices") is not None and not _choices(e["choices"]):
                out.append(f"{where}.thread[{j}].choices: at most {MAX_CHOICES}, each a label (at most {MAX_LABEL} characters)"
                           f" and a reply (at most {MAX_REPLY})")
    return out


def _inline_css(css: str) -> str:
    """Isolate page.html's shared design from the inline host's selectors and tokens.

    The template uses flat rules and @media groups. Reject new at-rules until their
    scoping is handled explicitly; never silently publish global inline styles.
    """
    root = "#discuss-root"
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"--(?!discuss-)([a-z][a-z0-9-]*)", r"--discuss-\1", css)

    def selectors(text: str) -> list[str]:
        parts, start, depth, quote = [], 0, 0, None
        for i, char in enumerate(text):
            if quote:
                if char == quote and (i == 0 or text[i - 1] != "\\"):
                    quote = None
            elif char in ("\"", "'"):
                quote = char
            elif char in "([":
                depth += 1
            elif char in ")]":
                depth -= 1
            elif char == "," and depth == 0:
                parts.append(text[start:i].strip())
                start = i + 1
        parts.append(text[start:].strip())
        return parts

    def scope(selector: str) -> str:
        if selector in (":root", "body"):
            return root
        if selector.startswith(":root"):
            return selector + " " + root
        if selector.startswith(root):
            return selector
        if selector.startswith(".wrap"):
            return root + selector
        return root + " " + selector

    def rules(text: str) -> str:
        out, i = [], 0
        while text[i:].strip():
            start = text.find("{", i)
            if start < 0:
                raise ValueError("inline CSS: expected a rule")
            prelude = text[i:start].strip()
            depth, end, quote = 1, start + 1, None
            while depth and end < len(text):
                char = text[end]
                if quote:
                    if char == quote and text[end - 1] != "\\":
                        quote = None
                elif char in ("\"", "'"):
                    quote = char
                elif char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                end += 1
            if depth:
                raise ValueError("inline CSS: unclosed rule")
            body = text[start + 1:end - 1]
            if prelude.startswith("@media "):
                out.append(prelude + " {\n" + rules(body) + "\n}")
            elif prelude.startswith("@") or "{" in body:
                raise ValueError("inline CSS: unsupported rule " + prelude)
            else:
                out.append(",\n".join(scope(s) for s in selectors(prelude)) + " {" + body + "}")
            i = end
        return "\n".join(out)

    return rules(css)


def render_state(state: dict, client: str = "claude", assistant: str | None = None) -> str:
    if client not in ASSISTANT:
        raise ValueError(f"client: one of {sorted(ASSISTANT)}")
    if assistant is not None and not NAME.match(assistant):
        # The name lands in HTML text and in script strings alike, so it takes no characters either would read.
        raise ValueError("assistant: 1-32 letters, digits, spaces, '.', '_' or '-'")
    state = {**state, "client": client}
    bad = problems(state)
    if bad:
        raise ValueError("state not rendered:\n  " + "\n  ".join(bad))
    template = Path(__file__).with_name("page.html").read_text(encoding="utf-8")
    if client == "codex":
        # Keep the original design, font links and shared interaction code. The host
        # also defines --muted and --accent, but as fills rather than text colors.
        style_start, style_end = template.index("<style>"), template.index("</style>")
        css = _inline_css(template[style_start + 7:style_end])
        css += "\n" + Path(__file__).with_name("codex.css").read_text(encoding="utf-8")
        template = template[:style_start] + "<style>\n" + css + "\n" + template[style_end:]
        template = re.sub(r'<meta name="claude:viewport-fit-sides"[^>]*>\n', "", template)
    template = template.replace("__ASSISTANT__", assistant or ASSISTANT[client])
    head, sep, tail = template.partition("__STATE__")
    if not sep or head.count("__TITLE__") != 1 or "__STATE__" in tail:
        raise ValueError("page.html must hold __TITLE__ once, then __STATE__ once")
    # "<" escaped so no text in the state can close the <script> that carries it.
    payload = json.dumps(state, ensure_ascii=False, indent=1).replace("<", "\\u003c")
    page = head.replace("__TITLE__", html.escape(state["title"])) + payload + tail
    if client == "codex":
        page = re.sub(r"^<title>.*?</title>\n", "", page)
    if client in ("browser", "hosted"):
        page = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' + page + '</html>'
    return page


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state", type=Path)
    parser.add_argument("output", type=Path, nargs="?")
    parser.add_argument("--client", choices=tuple(ASSISTANT), default="claude")
    parser.add_argument("--assistant", help="the name of whoever answers the page (default: the client's)")
    args = parser.parse_args(argv[1:])
    dst = args.output or args.state.with_suffix(".html")
    try:
        page = render_state(json.loads(args.state.read_text(encoding="utf-8")), args.client, args.assistant)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    dst.write_text(page, encoding="utf-8", newline="\n")
    print(f"wrote {dst} ({len(page.encode('utf-8')):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

