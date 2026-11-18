# discuss

An agent skill for working through a long numbered list with your AI assistant on a page instead of in chat.

When Claude or Codex hands you eight numbered questions, answering in chat means quoting and renumbering
by hand. `/discuss` puts the points on a page: one card per point with the assistant's position, a reply box
and two or three one-click answers written for that point, plus Close to settle it as it stands. You reply under the points you care about and
press **Send** once. The assistant answers every point and republishes, and the page reloads with the answers
and fresh boxes, round after round, until every point is settled. On a Claude Artifact page, the Codex
browser page or a page in a project's own app you can also paste a screenshot into any box, or drop an image on it.

A one-minute demo, with sound:

https://github.com/user-attachments/assets/d0226fa2-4af6-4462-9661-cb2f6545d44f

## Install

The skill is the folder itself. Clone it where your client looks for skills:

| Client | Command |
| --- | --- |
| Claude Code (all projects) | `git clone https://github.com/rballentine/discuss ~/.claude/skills/discuss` |
| Codex (all projects) | `git clone https://github.com/rballentine/discuss ~/.agents/skills/discuss` |
| One project only | clone into the project's `.claude/skills/discuss` or `.agents/skills/discuss` |
| Claude Code on the web (claude.ai/code) | commit the folder to the project as `.claude/skills/discuss`; a cloud session reads it from the repository |
| ChatGPT (web or desktop app) | zip the folder and add it under Plugins, Skills, Create, "Upload from your computer" |

Update with `git -C <that folder> pull`. The scripts need Python 3 and nothing else.

## Use

The assistant opens a page on its own when a reply would carry six or more numbered points you may want to
answer. For a shorter list, or one it left in chat, type `/discuss` (Claude Code) or `$discuss` (Codex),
optionally with a title or which list you mean. Asking for "a discussion page" works too.

## Keys

- **Enter** moves to the next box and collapses the point it leaves; **Shift+Enter** is a new line.
- **Ctrl+Enter** sends.
- **Alt+1** to **Alt+3** put that choice in the focused point's box.
- **Alt+0** closes the focused point (in its box, then moves on as Enter does) or reopens a closing one.
- **Ctrl+Space** collapses or expands the card in focus.
- **Ctrl+Alt+1** shows or hides closed points; **Ctrl+Alt+2** goes to "Add a point".
- **Enter in "Add a point"** turns the text into a new numbered point, folded and titled with its first
  words, and stays there for the next one; new points collapse like the others.
- **Tab** goes from box to box without collapsing anything; a collapsed card's title is a Tab stop so it can
  be opened. Tab in "Add a point" turns its text into a new point and moves to it, or, with the box empty,
  wraps to the first point (Shift+Tab there wraps back), so Tab never reaches the Send bar's buttons.

A box reached by keyboard scrolls to just above the Send bar, with its point's text above it. Boxes grow with
their text. Hovering a tag shows what it means.

## What each client needs

- **Claude Code:** the page is a [Claude Artifact](https://code.claude.com/docs/en/artifacts), so you need
  Artifacts: a Pro, Max, Team or Enterprise plan, signed in with your claude.ai account, in the CLI or the
  desktop app. **Send** saves your replies in the artifact's data store and wakes the session through an
  artifact comment. Where those aren't available to your account, the page's **Copy replies** button gives
  you the text to paste into chat instead.
- **Claude Code on the web (claude.ai/code):** the same Artifact page. A cloud session publishes it through
  the artifacts connector, and Send wakes that session the same way.
- **Codex desktop:** a local page served by `serve.py` on `127.0.0.1`; Send queues your replies into the
  chat with `codex queue`.
- **ChatGPT (web or desktop app):** the page appears inside a Work conversation. Send asks you to confirm a
  follow-up message, and each round's answers arrive as a new page in the next reply. Start the conversation
  on the web; you can carry it on in the desktop app. This page can't take pasted images.
- **Your own web app:** the `hosted` client runs the page in a sandboxed iframe that talks to your app over
  `postMessage`. See "Hosted" in [SKILL.md](SKILL.md).

## Contributing

Pull requests are welcome. `page.html` is shared by every client, so a fix for one must not break another:
run `python -m unittest discover -p "test_*.py"` in this folder before you send one.

## License

[MIT](LICENSE).
