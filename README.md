# discuss

An agent skill for working through a long numbered list with your AI assistant on a page instead of in chat.

When Claude or Codex hands you eight numbered questions, answering in chat means quoting and renumbering
by hand. `/discuss` puts the points on a page: one card per point with the assistant's position, a reply box
and two or three one-click answers written for that point. You reply under the points you care about and
press **Send** once. The assistant answers every point and republishes, and the page reloads with the answers
and fresh boxes, round after round, until every point is settled.

## Install

The skill is the folder itself. Clone it where your client looks for skills:

| Client | Command |
| --- | --- |
| Claude Code (all projects) | `git clone https://github.com/rballentine/discuss ~/.claude/skills/discuss` |
| Codex (all projects) | `git clone https://github.com/rballentine/discuss ~/.agents/skills/discuss` |
| One project only | clone into the project's `.claude/skills/discuss` or `.agents/skills/discuss` |

Update with `git -C <that folder> pull`. The scripts need Python 3 and nothing else.

## Use

After a reply with numbered points, type `/discuss` (Claude Code) or `$discuss` (Codex), optionally with a
title or which list you mean. Asking for "a discussion page" works too.

## What each client needs

- **Claude Code:** the page is a [Claude Artifact](https://code.claude.com/docs/en/artifacts), so you need
  Artifacts: a Pro, Max, Team or Enterprise plan, signed in with your claude.ai account, in the CLI or the
  desktop app. **Send** saves your replies in the artifact's data store and wakes the session through an
  artifact comment. Where those aren't available to your account, the page's **Copy replies** button gives
  you the text to paste into chat instead.
- **Codex desktop:** a local page served by `serve.py` on `127.0.0.1`; Send queues your replies into the
  chat with `codex queue`.
- **Your own web app:** the `hosted` client runs the page in a sandboxed iframe that talks to your app over
  `postMessage`. See "Hosted" in [SKILL.md](SKILL.md).

## Contributing

Pull requests are welcome. `page.html` is shared by every client, so a fix for one must not break another:
run `python -m unittest discover -p "test_*.py"` in this folder before you send one.

## License

[MIT](LICENSE).
