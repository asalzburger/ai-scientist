# Email and calendar integration

These modules run inside the scientist process. SMTP, IMAP, JMAP, and CalDAV connect
directly to your existing accounts; there is no connector service to deploy. The CLI
is the control surface, with an optional embedded read-only web dashboard.

The scientist will use its own account. Account details will be provided later;
local drafting, feedback, and offline testing do not depend on those credentials.

## Communication habits and feedback

The initial preferences in `config/communication.yaml` are brief questions in chat,
selective interruptions with related questions batched, and longer explanations by
asynchronous email. These guide content and channel choices, rather than prescribing
one permanent interface or rigid workflow. No numeric question quota, notification
schedule, or automatic delivery permission has been established.

```bash
ai-scientist communication preferences
ai-scientist communication feedback frequency "Batch nonurgent questions"
ai-scientist communication feedback priorities "Lead with work that unblocks the next step"
ai-scientist communication history
ai-scientist daily-review
```

Feedback accepts a dimension (`frequency`, `channel`, `length`, `clarity`, `priorities`,
or `usefulness`), a comment, and an optional `--reference` to an email, briefing, or
interaction. It persists with a human-authored audit event. The latest 20 feedback
records are supplied to the scientist on future model calls. Adaptation currently
means using this feedback in reasoning and drafting; it does not train model weights,
rewrite preferences automatically, or measure interruption frequency yet. Feedback
text cannot authorize external effects or change approval policy.

`daily-review` generates and saves an unsent briefing draft focused on what matters
today to move work forward: ordered next actions, why they matter, blockers, and
decisions needed. It does not dump all tasks, mark work done, send, or schedule a
briefing. Saved briefings are available in the dashboard's Daily priorities view,
with IDs that can be referenced in feedback. Model-backed drafting needs the model
API configured; saving feedback does not.

## Start offline

From the repository root, after following the README installation instructions:

```bash
ai-scientist init
ai-scientist contacts add "Example colleague" colleague@example.org --timezone Europe/Zurich
ai-scientist contacts list
ai-scientist mail draft --to colleague@example.org "Meeting proposal" /path/to/body.txt \
  --sender scientist@example.org
ai-scientist mail drafts
ai-scientist mail show MAIL-REPLACE-ME
ai-scientist calendar draft "Planning" 2026-10-19T09:00:00+02:00 2026-10-19T10:00:00+02:00 \
  --timezone Europe/Zurich
ai-scientist calendar drafts
ai-scientist calendar export EVENT-REPLACE-ME
ai-scientist web
```

Use the IDs printed by the draft commands. `mail draft` reads a UTF-8 body file;
repeat `--to`, `--cc`, or `--bcc` for additional recipients. The web command prints
a local access link. Open that exact link to review saved records. Its access token
stays in browser memory; refresh by reopening the terminal link. The dashboard does
not issue approvals or execute external actions. Stop it with Ctrl-C.

With the model API configured, the scientist can write the draft body:

```bash
ai-scientist mail compose "Ask for a short planning meeting next week; don't propose an unverified time" \
  --to colleague@example.org "Meeting proposal" --sender scientist@example.org
```

This command sends the drafting instructions, recipient, subject, and current
workspace context to the model and saves its response as an unsent draft. It does
not send the email. Review factual statements and commitments before approval.
Imported email is not automatically included in model context. `mail reply` accepts
a user-supplied body file and preserves the original Message-ID/References chain.

## Configure accounts

Set only the environment variables for the protocols you use. Passwords and bearer
tokens are read from the environment and never stored in application records or
audit events. `.env` files are not loaded automatically. Use a dedicated account
or the credentials supported by your mail/calendar administrator.

| Protocol | Required variables | Optional defaults |
|---|---|---|
| SMTP | `AI_SCIENTIST_EMAIL`, `AI_SCIENTIST_SMTP_HOST`, `AI_SCIENTIST_SMTP_USERNAME`, `AI_SCIENTIST_SMTP_PASSWORD` | `AI_SCIENTIST_SMTP_PORT=465`, `AI_SCIENTIST_SMTP_SECURITY=tls` |
| IMAP | `AI_SCIENTIST_IMAP_HOST`, `AI_SCIENTIST_IMAP_USERNAME`, `AI_SCIENTIST_IMAP_PASSWORD` | `AI_SCIENTIST_IMAP_PORT=993` |
| CalDAV | `AI_SCIENTIST_CALDAV_URL`, `AI_SCIENTIST_CALDAV_USERNAME`, `AI_SCIENTIST_CALDAV_PASSWORD` | `AI_SCIENTIST_CALDAV_TIMEZONE=UTC` |
| JMAP | `AI_SCIENTIST_JMAP_URL`, `AI_SCIENTIST_JMAP_ACCOUNT_ID`, `AI_SCIENTIST_JMAP_TOKEN` | None |

For SMTP submission on port 587, set security to `starttls` and port to `587`.
There is no plaintext SMTP mode. IMAP uses TLS. CalDAV requires the final HTTPS
**calendar collection URL**, not the server home page. JMAP requires the final HTTPS
**API URL** and account ID from your provider's JMAP session. Redirects are rejected.
OAuth login flows and Exchange/Google-specific APIs are not implemented.

## Read mail

```bash
ai-scientist mail sync --limit 20
ai-scientist mail inbox
ai-scientist mail reply MESSAGE-REPLACE-ME /path/to/reply.txt
```

IMAP opens the mailbox read-only and uses UID-based `BODY.PEEK[]` fetches. It does
not mark messages read, delete messages, or change flags. Local IDs include account,
folder, UIDVALIDITY, and UID, making repeat imports idempotent. IMAP imports at most
100 messages per call and rejects messages larger than 1 MB. Attachments and HTML
bodies are not imported; HTML-only mail is visibly labelled.

Use `mail sync --provider jmap` for read-only JMAP import. `--folder` is a JMAP
mailbox ID, or `INBOX` to resolve the inbox role. JMAP requests cap body values at
100 KB, mark truncation, and cap responses at 5 MB. This is a bounded recent-message
import, not full mailbox synchronization. Remote deletions are not mirrored locally.

## Approve and send

```bash
ai-scientist mail request-send MAIL-REPLACE-ME
ai-scientist approval show OP-REPLACE-ME
ai-scientist approval grant OP-REPLACE-ME
ai-scientist mail send OP-REPLACE-ME
```

`request-send` freezes the exact draft, including recipients and invitation content,
and the configured SMTP account. It performs no network I/O. `grant` displays this
snapshot and asks the human to confirm; it then prints a secret token. `send` asks
for that token through hidden terminal input, avoiding shell-history exposure.
Requests expire one hour after creation. Changes to the draft after a request do not
change that request: review the snapshot, and create a new request for a changed draft.
Declining the confirmation revokes the request. Use `approval revoke OP-REPLACE-ME`
to revoke a pending request or an unused token. An operation already executing
cannot be cancelled through this mechanism.

The approval service requires `approval_required` in policy, a matching action and
account, an intact payload fingerprint, an unexpired token, and an atomic transition
from approved to executing. Concurrent or repeated execution is rejected. Raw tokens
are not persisted. Changing configuration to `autonomous` cannot bypass this gate.
The legacy action-only `policy.Approval` is not accepted by these integrations.

SMTP success means the server accepted all envelope recipients, not that their
inboxes received the message. Bcc recipients appear only in the envelope. A partial
refusal, timeout, or exception after execution starts leaves the operation
`uncertain`; a process crash can leave it `executing`. Neither can be replayed.
Inspect the server and operation status before preparing a new draft. There is no
automatic retry, reconciliation, Sent-folder append, or delivery-status tracking.
Expired requests also require a fresh draft; token renewal is not implemented.

## Calendar workflow

```bash
ai-scientist calendar draft "Weekly planning" 2026-10-19T09:00:00+02:00 2026-10-19T10:00:00+02:00 \
  --timezone Europe/Zurich --frequency WEEKLY --count 6
ai-scientist calendar request-publish EVENT-REPLACE-ME
ai-scientist approval grant OP-REPLACE-ME
ai-scientist calendar publish OP-REPLACE-ME
ai-scientist calendar availability 2026-10-19T08:00:00+02:00 2026-10-19T18:00:00+02:00 --minutes 30
```

Local event drafts persist independently of external calendars. Publication creates
a personal CalDAV event using a conditional PUT (`If-None-Match: *`); an existing
resource cannot be overwritten by this operation. Availability queries read the
configured remote calendar live and subtract merged busy intervals from the supplied
window. Failed reads never imply free time. Local unpublished drafts and other
people's calendars are not included. The dashboard shows local drafts, not a synced
remote agenda.

Event times are stored in UTC; recurrence retains a named timezone for local wall
time. Draft recurrence supports DAILY, WEEKLY, and MONTHLY, with a required count of
1–366. Query windows are limited to 366 days. Imported availability supports all-day
events and skips cancelled/transparent entries. Remote recurring events must be
expanded by the CalDAV client/server; unexpanded rules fail closed. Floating and
all-day remote times use `AI_SCIENTIST_CALDAV_TIMEZONE`, which must match the calendar.
Arbitrary recurrence edits, exceptions, cancellations, and RSVP ingestion are future work.

Prepare meeting invitations separately:

```bash
ai-scientist calendar invite EVENT-REPLACE-ME --to colleague@example.org
ai-scientist mail show MAIL-REPLACE-ME
```

This creates an email draft containing an iCalendar `METHOD:REQUEST` attachment.
Use the email approval flow to send it. CalDAV publication never sends attendee
invitations, and approving a personal calendar event does not approve an email.

## State and boundaries

- `communications/`: validated drafts, reply composition/threading, a shared mailbox
  service, and SMTP/IMAP/JMAP adapters. `MailReader` and `MailDelivery` define interfaces.
- `calendar/`: typed events, recurrence, invitations, availability, and a CalDAV
  implementation of the `CalendarProvider` interface.
- `contacts/`: validated local contacts with exact, ambiguity-checked lookup.
- `approvals/`: durable operation snapshots and one-use human authorization.
- `web/api/`, `web/ui/`: authenticated read-only review views, served on loopback.
- `storage.py`: document persistence and operation transitions with atomic audit entries.

All drafts, imported mail, contacts, and approval snapshots live in the existing
SQLite database under the Git-ignored `state/` directory. This database is plaintext
and belongs to the local user; encryption and retention controls remain future work.
External message content is untrusted data and is never rendered as HTML or given
approval authority. The application does not expose the approval-grant function to
the model or the web API. Approval authority assumes a trusted local human/process;
it is not a multi-user identity or access-control system.

Mattermost notifications, Zoom participation, scheduled polling, OAuth account setup,
web editing, and JMAP sending remain separate follow-up modules.

Protocol references: [Python SMTP](https://docs.python.org/3/library/smtplib.html),
[Python IMAP](https://docs.python.org/3/library/imaplib.html),
[JMAP Mail](https://www.rfc-editor.org/rfc/rfc8621.html),
[CalDAV](https://caldav.readthedocs.io/), and
[iCalendar](https://icalendar.readthedocs.io/).
