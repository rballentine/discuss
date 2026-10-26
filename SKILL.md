---
name: discuss
description: "Work through numbered points on a page with a reply box under each point and one Send button: a Claude Artifact page, a local browser page for Codex, or a page hosted in a project's own web app. Start only when the user invokes /discuss, $discuss, or asks for a discussion page. Also use for replies starting [/discuss and related chat while a discussion is open."
argument-hint: "[title, or which list]"
---

# /discuss - a page for working through numbered points

When a reply carries many numbered points, answering them in chat means quoting
and renumbering by hand. This skill puts the points on an Artifact page: one
card per open point with Claude's current position, a reply box and two or
three **choice buttons** written for that point; there are no generic Agree /
Say more / Drop buttons. Hovering a choice shows the reply it
stands for at once; clicking it, or Alt+1 to Alt+3 in the point's box, puts that
reply in the box to edit or send (Ctrl+Z brings back what was typed there). The
recommended choice's label is bold; the chosen one gets a tick. The user writes under
the points they care about and presses **Send to Claude** once. The page saves the replies in its store and sends Claude a
one-line comment naming them, which wakes this session without pasting every
reply into its chat; Claude answers every point, republishes,
and the page reloads with the answers and fresh boxes.

Sent replies stay in their boxes, through reloads, until Claude answers. The
user can change one and press Send again: that follow-up carries only what
changed. A successful send shows a confirmation banner and Sent tags; the Send
button stays in its sent state until a reply changes. Closed points are hidden
by default. "Show closed points" reveals them in numerical order among the open
points, and says how many closed this round. These UI rules apply to every client.

**The page holds the answers; chat doesn't repeat them** (reading everything
twice is the cost this skill exists to remove). After each round, chat
gets one line, a tally such as "Round 2 answered: 4 closed, 3 still open", plus only
what fits under no point: a problem hit along the way, a blocker, or a step the user
must take outside the page. Never restate a point's answer, list what each point
says, or summarize the work a point already describes.

Keys: Enter moves to the next box and collapses the point it leaves,
Shift+Enter is a new line, Ctrl+Space collapses or expands the card in focus,
Ctrl+Enter sends, Alt+1 to Alt+3 put that choice in the focused point's box,
Ctrl+Alt+1 shows or hides closed points and Ctrl+Alt+2 goes to "Add a point". Enter in
"Add a point" turns the text into a new numbered point, folded and titled with
its first words, and stays there for the next one; new points collapse like
the others. Tab goes from box to box without collapsing anything; a collapsed
card's title is a Tab stop so it can be opened. Tab in "Add a point" turns its
text into a new point and moves to it, or, with the box empty, wraps to the
first point (Shift+Tab there wraps back), so Tab never reaches the Send bar's
buttons. A box reached by keyboard scrolls to just above the Send bar, with its
point's text above it. Boxes grow with their text. Hovering
a tag shows what it means.

Files: `page.html` (shared UI and round logic), `render.py` (embeds state and
selects the client), `codex.css` (Codex's theme) and `serve.py` (Codex's local
page server). Edit only state for a discussion. In the commands below, `<skill>`
is the folder holding this file; run the scripts with Python 3.

## Choose the client

The workflow above describes Claude's Artifact delivery. In **Codex desktop**,
use the local browser page below. Keep all reply boxes together on one page, as
in Claude, rather than a native question form. Keep the same numbered state
and answering rules in every client.

**A project's own host comes first.** If the project's instructions or your system
prompt name a host for discussion pages (for example, a page served by the
project's own web app, answered from a chat thread), follow them: they say where
the state lives, how a round is published and how replies come back, and they win
over the defaults here. Such a host uses the **hosted** client below. Everything
under "Start a discussion" and "Answer a round" still applies.

`page.html` is shared: layout, keyboard, draft, and sent-state fixes affect every
client. Delivery differs: Claude uses Artifact comments/store and republishing;
a project host uses its own publish step and its app; Codex uses `serve.py`, the
CLI queue, and the same local JSON for each new round.
Keep host-specific behavior in its client branch; do not fork the page template.

### Hosted: a page inside a project's web app

For a project that serves discussion pages from its own app. The page runs in a
sandboxed iframe with no storage and talks to its parent only through
`postMessage` on the `discuss/1` bridge (the requests are listed in `page.html`):
`send` delivers a round's replies, `draft` saves unsent replies, `version`
reports the latest round, and `reload` shows it. The app either renders the page
with `python <skill>/render.py STATE.json PAGE.html --client hosted --assistant NAME`
or makes the same substitutions itself; if it reimplements `problems()`, it keeps
the wording identical, so both refuse the same states the same way. The project's
instructions cover the rest.

### Codex: browser discussion page

1. Save the usual JSON state in the task's durable visualization/output directory,
   outside git. Use `who: "codex"` for answers. Obtain the actual current chat UUID
   from the task context/tool metadata; never guess a target or use a title match.
2. Confirm `codex queue --help` is available. Start this temporary local server in
   a retained terminal session:
   `python <skill>/serve.py STATE.json --thread CHAT_UUID`.
   It binds only to `127.0.0.1`, prints its URL, and records `browser_url` and
   `thread_id` in the state. Reuse a running server for that discussion; do not
   register a scheduled task, deploy anything, or start a competing agent session.
3. Open that HTTP URL with the browser tools or `open_in_codex`, and return a
   clickable URL. Keep a user-facing browser tab as a deliverable. The actual
   browser page supplies all reply boxes and the Send button.
   Do not substitute an inline visualization or raw `file:` preview.
4. **Send** stores a submission in `<slug>-replies/<UUID>.json` next to the state,
   then uses the documented `codex queue --thread UUID --message TEXT` command
   to queue one short Markdown link, `/discuss · replies to round N`, into this
   chat. The linked receipt carries the full replies and state path; keep paths,
   UUIDs and procedural instructions out of the visible message. This avoids Windows' command-length
   limit for long replies. The target is fixed at server launch. No shell command
   is assembled from reply text. "Queued" is acceptance by the queue, not proof
   that the agent has answered. Test only with an unmistakably assistant-generated
   transport probe, never a fabricated user approval.
5. An incoming `[/discuss ...]` message may be a Markdown link to a local
   submission JSON instead of carrying its full text. Read the link target's
   `text` field and load the JSON at its `state` path (older messages name the
   state directly in the message). Process each submission only once: append its UUID to the state's
   `processed_submissions` when completing the round. For a synthetic transport
   probe, acknowledge the transport only; do not treat it as a user's decision.
6. **Answer on the same page:** append user/assistant entries and outcomes, advance
   `round`, preserve `browser_url`/`thread_id`, and replace the same JSON atomically
   (write a sibling temporary file, then `Path.replace`). The server renders the
   current JSON on each load, so no separate render command is needed. The browser
   polls its local version and refreshes once a newer round exists and no edits
   remain unsent. The terminal server must remain running while the user uses it;
   stop that owned process when the discussion is finished or the user asks.

The server rejects cross-origin submissions and serves only this discussion, not
a directory of files. Delivery failures leave drafts and saved submissions intact.
Unknown delivery outcomes are not automatically retried; inspect the chat before
requeuing. Copy replies remains a fallback. If the CLI cannot reach the current
desktop chat, say so; do not silently replace the requested browser workflow.

Verification: `python -m unittest discover -s <skill> -p "test_*.py"`:
`test_serve.py` covers endpoint boundaries,
idempotency, uncertain delivery, and long replies; `test_render.py` renders every
client from the shared page, so a fix for one can't silently break another.
Browser tests must additionally exercise actual text entry, Send, and round refresh.
The [official CLI reference](https://learn.chatgpt.com/docs/cli/reference#codex-queue)
documents the queue command.

### Codex: native reply form (only if requested)

Use `functions.request_user_input_async` when available. Each `questions` entry
has a `title` containing the point number, title, and your current position, and
`options` from the point's choices (see the state format below). The user can also type their own reply. Include only open points, and keep the questions concise. For a long list,
present a few related points at a time; preserve their original numbers. Do not
use the Plan-only `request_user_input` tool in Default mode.

Save the usual JSON state in the task's visualization/output directory. Native
replies need no `[/discuss]` prefix: map them to the numbers in the pending form,
append them to the state, do accepted work, and answer each point. Show the next
round's answers in chat and open a fresh form for anything still requiring input.
Never treat a preselected option or lack of a reply as agreement. Do not repeatedly
reissue a form while its answers are pending. If the tool is unavailable, use
numbered chat replies and say so rather than promising an interactive page.

**Observed limitation (2026-10-22):** in Codex desktop the inline HTML discussion
rendered but could not be clicked or typed into. The page's browser
tests used a mock host and did not establish live chat interactivity. Opening the
raw HTML with `open_in_codex` also does not supply the visualization host bridge.
Do not say "use the form directly below" based only on rendering or mock tests.

### Codex: optional HTML preview

Use this only when the user asks for an inline preview or live interaction has been
verified in the current client. If it behaves like an image, use the browser page;
do not keep emitting the same preview or opening its raw HTML as a fix.

- Store `<slug>.json` in the thread's visualization directory supplied in the
  environment, or a durable task-owned output directory. Use a unique slug in
  this chat. Do not put private discussion state into git.
- Use `who: "codex"` for your answers (`claude` remains valid for old history).
  Render `python <skill>/render.py STATE.json ROUND.html --client codex`.
  Use a new output filename for each round, e.g. `<slug>-r2.html`, keeping the
  JSON file as the current source of truth.
- Display the HTML in the final response with the native inline reference:
  `visualize{"path":"/absolute/thread/path/<slug>-r2.html"}`.
  A file tab or ordinary browser does not supply the Codex send bridge.
- **Send to Codex** calls `window.openai.sendFollowUpMessage({prompt, title})`.
  It opens the host's confirmation. A resolved promise does not prove delivery,
  so replies remain drafts and resendable. Each send includes the current replies;
  reconcile repeated sends against the latest state, without executing an accepted
  action twice. For an old-round reply, retain newer answers and decisions, merge
  only new user intent, and ask only if it conflicts with a later decision.
- Answers appear in a **new inline page in the next response**. Old pages do not
  refresh. Do not use Artifact tools, comment watches, or scheduled polling here.
- Drafts use `window.openai.widgetState` / `setWidgetState` in `privateContent`,
  keyed by slug and round. No draft is implicitly sent as model context. State
  snapshots stay below 16 KiB; larger drafts remain in the open view with a copy
  warning. Sends carry the full text, without Claude's 4 KB comment/store path.
- If the bridge is unavailable or rejects a send, **Copy replies** exposes the
  exact text to paste into this chat. Never claim a send or persistence succeeded
  just because HTML rendered. Validate the host handoff with a real user send;
  browser tests with a mock bridge verify only the page's side of the contract.

The installed `visualize` skill documents this bridge and inline reference.
On CLI clients without the inline host, provide the rendered page with Copy
replies as the fallback. The rules below still govern answering each point;
"Claude" means the current assistant. Claude's publish/watch/comment steps apply
only in Claude.

## Start a discussion

1. **Take the points.** The invocation text names the list or gives it; with no
   text, use the most recent numbered list in this conversation, yours or the
   user's. Keep the original numbers. For each point write:
   - `title`: the point in at most eight words.
   - Claude's round-1 text: your full current position, readable on its own,
     because the page is where the user reads it. Lead with the answer or
     recommendation; about 120 words at most.
   - **When the list is the user's own** (they wrote or pasted it, rather than
     you enumerating it), each thread opens with their point, verbatim, before
     your answer: `{"who": "you", "round": 1, "text": ...}`, holding every word
     and sub-bullet of that point with only its number removed. The `title`
     summarizes it; it never replaces it.
   Pick a `slug` (at most 24 characters, `a-z0-9-`) and a short `title` for the
   whole page; `topic` is an optional one-line context.
2. **Write the state** to the Codex or project-host location above, or
   `<scratchpad>/discuss/<slug>.json`, where `<scratchpad>` is the session's
   scratch or temporary directory. On Windows keep the names short: a session
   scratchpad path can already be about 195 characters, and MAX_PATH is 260.

   ```json
   {
     "slug": "fee-job",
     "title": "Fee job redesign",
     "topic": "Open points from the redesign review",
     "round": 1,
     "updated": "2026-10-22 14:05",
     "items": [
       {"n": 1, "title": "Run it nightly or weekly?", "status": "open",
        "thread": [{"who": "claude", "round": 1, "text": "Weekly. ...",
                    "choices": [{"label": "Weekly", "reply": "Weekly, Mondays 06:00 ET."},
                                {"label": "Nightly", "reply": "Nightly at 02:00 ET; alert only on a failure."}]}]},
       {"n": 2, "title": "Email the bookkeeper the books?", "status": "open",
        "thread": [{"who": "you", "round": 1, "text": "can the job email the books to the bookkeeper when it finishes?"},
                   {"who": "claude", "round": 1, "text": "Yes. ...",
                    "choices": [{"label": "Email them", "reply": "Yes, email the books to the bookkeeper when the job finishes."},
                                {"label": "I'll send them", "reply": "No email; I'll send the books myself."}]}]}
     ]
   }
   ```

   `status` is `open`, `done`, `parked` or `dropped`; a closed point also needs
   `outcome`, the one line its folded card shows. Text takes light markdown:
   paragraphs, `- ` and `1. ` lists, `` `code` ``, `**bold**`, `[text](https://...)`.

   **Choices**: every answer on an open point carries two or three `choices`
   written for that point, your recommendation first (the page bolds it). Even
   a simple pair such as "This works." / "Try again." helps: it tells the user
   what the point needs from them. Where the point is a
   decision, the choices are its options. `label` is one to three words, at
   most 24 characters; `reply` is what the user would send, in their voice and
   specific enough to act on alone, at most 300 characters. The page shows a
   point's choices only while it is open and that answer is its latest, so
   every new answer on an open point brings its own.
3. **Present the round.** In Codex, use the browser page above (or the optional
   HTML path when appropriate). With a project host, publish as its instructions
   say and skip step 4. In Claude, render and publish:
   `python <skill>/render.py <scratchpad>/discuss/<slug>.json`
   writes `<slug>.html` beside it (it refuses a malformed state and says why).
   Publish that file with the Artifact tool:
   `capabilities: {"comments": {}, "db": {}}` (`db` carries the replies; the
   comment only names them), `icon: "chat"`, a one-sentence `description`. Add the returned
   `url` to the state as `"url"`.
4. **Check the watch (Claude Artifact only).** The Send button only wakes this session while the
   artifact's watch says comment auto-replies are armed. Read the publish
   result's subscription line; if it does not say armed, run
   `ArtifactComments` `action: "watch"` with no `url` to see the listing. If it
   cannot be armed, or the Artifact tool or its comments are not available in
   this session, tell the user the page's **Copy replies** button is the way
   back (they paste the replies into chat). Without the Artifact tool, give them
   the rendered `<slug>.html` to open in a browser; it works the same, with
   Copy replies in place of Send.
5. **Tell the user** in one line: the page, and that they reply under any
   points and press Send. The first send on each new page asks them once to
   let the page comment as them in Claude. With a project host, its reply carries
   the link. In Codex, link the browser page and
   tell them to use Send; only the optional inline bridge uses a send confirmation.

## Answer a round

A round arrives as an `[Artifact comment sent to Claude]` turn (with a project
host, whatever turn its instructions describe) whose quoted text
starts `[/discuss · <slug> · replies to round <N> ...]`, followed by
`#<n>: <reply>` blocks and perhaps `New point #<n>: <text>`. A later send in the
same round starts `follow-up to round <N>` and carries only changes: `#<n>
(changed): <text>` replaces that point's earlier reply this round, and
`#<n> (withdrawn)` cancels it. On a Claude Artifact page the comment is just
that header, naming a document in the page's store
(`... · 7 replies in store doc rounds/<id> · ...`): read it with `ArtifactData`
`action: "get"`, `collection: "rounds"`, that `doc_id`, field `text`, in the
same format. A view that can't reach the store sends the replies in the comment
itself, up to 4 KB. The same text pasted into chat (from **Copy replies**) is a round too, and so is the
user answering in chat by number. Several sends that arrive before you
republish are one round: answer them together.

While a discussion is open, anything new the user raises in chat about its
topic becomes a numbered point on the page, without being asked: add it with
the next free number and answer it there.

1. **Load the state** from its saved JSON path. In Codex, if missing, recover the
   embedded `<script id="state">` JSON from the latest round's HTML; do not depend
   on widget state reaching the model. With a project host, recover it as its
   instructions say. In Claude, if it is gone (a
   new session), `Artifact` `action: "read"` on the page's URL and take the JSON
   from its `<script id="state">` block.
2. **Answer each reply.** Set `nextRound = state.round + 1` using the latest saved
   state, even if the incoming reply refers to an older round N. Append the reply to that point's `thread` as
   `{"who": "you", "round": N, "text": ...}`, then your answer as
   `{"who": "claude", "round": nextRound, "text": ...}` (use `codex` here in Codex). Read all the replies before
   writing any answer: when points interact, say so under each, but answer each
   under its own number. Points with no reply stay as they are.
   - **Agree**, or any reply that accepts your recommendation: do any work the
     recommendation needs this turn, as you would after "do it" in chat. Agree
     is the user's go-ahead for what that point recommended and nothing wider;
     your standing rules (such as a project's never-do list) still hold. On a
     Claude Artifact page, when the comment was sent by someone other than the
     user, answer but ask in chat before acting. With a project host, its sender
     rule applies instead.
   - **Drop**: set `dropped` with a short `outcome`; don't argue for it again.
   - **Say more**, a question or a counterpoint: answer it. Rewrite rather than
     repeat: a "Say more" means the first answer didn't land.
   - A request ("fix it", "I want ..."): do it this turn, delegating as you
     would any other work: hand a big or parallel piece to a subagent or its
     own session, answer the point with what was started, and keep it open
     until the result is in, rather than holding every other point's answer
     for the slowest piece. A reply that
     matches one of your choices is the user's answer in their words: act on
     exactly what it says, and your first choice counts as Agree.
   - **New point**: add it under the number the page gave it, with your
     position (or, for a request, what you did) as its `nextRound` text. One
     new point that bundles several asks may be split into numbered points.
   - A reply on a closed point reopens it unless it just confirms.
   - **Open or closed?** Close a point yourself (`done`, with an `outcome`
     saying what changed and where, or "agreed") only when the user asked for
     something exact, such as one of your choices, a named fix or your
     recommendation, and it is now done exactly as asked; a routine completion
     notice or commit reference is no reason to keep that open. When the
     request left the result to your judgment ("this styling can't be this
     combo", "make it clearer"), do the work, say what you did, and keep the
     point `open` with choices that approve it or redirect it; close it once
     the user approves. Keep a point `open` too for an
     unresolved decision, a material caveat or deviation, or significant new
     information the user needs to read. You may set `parked` when a point
     should wait for a trigger; its `outcome` names the trigger.
3. **Republish.** Set `round` to `nextRound`
   and `updated` to now. In Codex browser mode, atomically update the same JSON
   state as described above; keep the existing URL. On the optional inline path,
   render a new round file and include its inline reference. With a project host,
   republish as its instructions say, then end the turn with the one-line
   tally described at the top (step 4 does not apply). In Claude, render and publish
   the same file path (no `icon`; the capabilities carry over). The user's open
   page reloads with the answers.
4. **Close the comment threads (Claude Artifact only).** In each thread the round came in, reply with
   one line ("Round N answered on the page: 3 done, 1 still open") via
   `ArtifactComments` `action: "reply"`, then `action: "resolve"`, so threads
   don't pile up. Chat gets the one-line tally described at the top, and nothing
   the page already says.

## When every point is settled

Say so in chat in one line; the page's closed points already list the decisions.
A decision that should outlast the session goes wherever the project keeps its
decisions (the repo, a doc, a ticket); the page is not a record.

## Claude Artifact limits

- The comment is what the session's chat shows, so every send is saved to the
  page's store (`rounds/r<N>-<id>`) and the comment only names the document; the
  store keeps every send. Only if the store write fails does the comment carry
  the replies, and a comment carries at most 4 KB.
- Unsent and sent replies, new points and collapsed cards live in the user's
  browser storage, keyed by slug and round, so a new round starts clean.
- Only the page's editors can send to Claude. Anyone else can use
  **Copy replies**.
