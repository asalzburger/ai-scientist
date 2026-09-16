# AI Scientist V0

A small, runnable foundation for a persistent scientific agent. It separates reasoning, durable state, external tools, and approval policy so later Gmail, Calendar, Zoom RTMS, GitHub, CERN batch, and literature integrations have a safe place to attach.

## Quick start

```bash
python3 -m venv .venv  # Python 3.11 or newer
source .venv/bin/activate
pip install -e '.[dev]'
ai-scientist init
ai-scientist status
```

To use the model-backed chat command, export an API key:

```bash
export OPENAI_API_KEY='...'
ai-scientist chat "What should I focus on next?"
```

The OpenAI Python SDK reads `OPENAI_API_KEY` from the environment. The default model can be changed using `AI_SCIENTIST_MODEL`.

## Useful commands

```bash
ai-scientist init
ai-scientist add-task "Try the scientist" --priority high --next-action "Review the CLI"
ai-scientist tasks
ai-scientist update-task TASK-REPLACE-ME --status done
ai-scientist tasks --all
ai-scientist remember "Current focus" "Make the scientist usable" --category decision
ai-scientist notes
ai-scientist status
ai-scientist chat "Prepare today's research plan"
pytest
ruff check .
```

Run commands from the repository root. `init` creates an empty workspace; use
`init --example` to add the optional NODD project. Existing records are preserved.
Replace `TASK-REPLACE-ME` with the ID returned by `add-task`. Tasks do not need a
project. `--project` must refer to an existing project. Deadlines use ISO 8601 with
a timezone, for example `--deadline 2026-10-01T12:00:00+02:00`, and are stored in UTC.

Tasks, notes, and decisions survive restarts in `state/scientist.db`. The latest 20
notes and decisions are included in each chat request, alongside the bounded task
and project snapshot. Chat itself is advisory: it cannot save tasks or notes, and
conversation history is not retained. Use the explicit commands to save anything
you want available next time. Notes are context, not validated scientific evidence.
Chat sends the assembled workspace context to the configured model provider.

Local state, `.env` files, and the virtual environment are ignored by Git. Configure
secrets through exported environment variables; `.env` files are not loaded automatically.
Task management and notes work without an API key or network access.

## Email and calendar

The scientist can write and save email drafts, import mail through IMAP or JMAP,
prepare calendar events and invitations, and inspect CalDAV availability. SMTP sends
and CalDAV event creation require explicit, expiring, single-use human approvals.
Everything runs as small Python modules inside the application.

```bash
ai-scientist mail --help
ai-scientist calendar --help
ai-scientist contacts --help
ai-scientist approval --help
ai-scientist communication --help
ai-scientist daily-review
ai-scientist web
```

See [the communication guide](docs/communications.md) for account configuration,
offline drafting, the review dashboard, and the exact approval workflow. No accounts
are connected automatically. Mattermost and Zoom remain future integrations.

## Architecture

```text
CLI / scheduler
      |
      v
ScientistAgent -----> OpenAI Responses API
      |
      +---- ContextBuilder ---- SQLite state
      |
      +---- PolicyEngine ---- approvals + audit log
      |
      +---- Tool adapters ---- Codex / later integrations
```

See `PROJECT.md` for scope and roadmap, `AGENTS.md` for development rules, and `docs/architecture.md` for boundaries.

## Safety posture

The scientist can read local state, plan, and draft. Email delivery and calendar
creation require matching durable approval tokens. Other consequential integrations
are not implemented. Prompts alone cannot override the email/calendar approval gate.

## License

No license has been selected. Add one before public distribution.
