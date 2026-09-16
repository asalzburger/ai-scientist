# AI Scientist V0

A small, runnable foundation for a persistent scientific agent. It separates reasoning, durable state, external tools, and approval policy so later Gmail, Calendar, Zoom RTMS, GitHub, CERN batch, and literature integrations have a safe place to attach.

## Quick start

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
ai-scientist init
ai-scientist status
```

To use the model-backed chat command, export an API key:

```bash
export OPENAI_API_KEY='...'
ai-scientist chat "What should we do next for NODD?"
```

The OpenAI Python SDK reads `OPENAI_API_KEY` from the environment. The default model can be changed using `AI_SCIENTIST_MODEL`.

## Useful commands

```bash
ai-scientist init
ai-scientist add-task "Run baseline material scan" --project nodd --priority high
ai-scientist status
ai-scientist chat "Prepare today's research plan"
pytest
ruff check .
```

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

V0 can read local state, plan, draft, and create isolated tasks. Sending messages, changing calendars, merging code, submitting papers, spending money, and changing production systems are blocked unless a future integration supplies a matching explicit approval. Prompts alone cannot override this boundary.

## License

No license has been selected. Add one before public distribution.

