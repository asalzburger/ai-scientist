# AI Scientist — Project Charter

## Product statement

Create a persistent AI scientist that behaves like a bounded member of a research team: it knows its responsibilities, maintains tasks and projects, prepares for meetings, runs reproducible studies, drafts communication and papers, and delegates software engineering to Codex.

## Current milestone: V0 Scientist Shell

V0 proves the core operating model before adding broad autonomy.

### In scope

- Scientist identity and policy configuration
- Typed projects, tasks, experiments, papers, meetings, people, claims, and evidence
- SQLite persistence outside model context
- Daily-status context assembly
- Responses API chat entry point
- Approval gate for consequential actions
- A bounded Codex delegation adapter
- CLI and unit tests

### Out of scope

- Autonomous email sending
- Calendar mutation
- Live Zoom participation or recording
- Production CERN/batch access
- Automatic pull-request merging
- Autonomous paper submission
- Unsupervised scientific conclusions

## First project: NODD

Objective: evolve OpenDataDetector into a realistic open detector representative of modern HL-LHC tracking technology.

Initial research questions:

1. How does the current ODD material budget differ from modern HL-LHC trackers?
2. Which components dominate that difference?
3. Which module, support, cooling, powering, and service models should replace current approximations?
4. How should layout and timing capability evolve?

First proposed experiment: a reproducible geantino material scan comparing a pinned ODD baseline with a realistic-services variant, reporting X/X0 versus eta with geometry and software provenance.

## Roadmap

| Version | Outcome |
|---|---|
| V0 | Persistent scientist shell, state, policy, CLI |
| V1 | Literature, GitHub, Drive, notebook, citations |
| V2 | Codex delegation, containers, experiment execution and result ingestion |
| V3 | Calendar/email/meeting preparation and Zoom RTMS transcript ingestion |
| V4 | Scheduled daily operation and deadline monitoring |
| V5 | Hypothesis generation with critic review and evidence-gated claims |

## Success criteria for V0

- The scientist can report its identity and active work from the database.
- Restarting the process preserves tasks, projects, experiments, and audit events.
- A consequential action is impossible without a matching approval.
- A user can initialize, inspect, and chat with the system through the CLI.
- The test suite runs without an API key or network access.

## Key decisions

- Python is the initial harness language.
- SQLite is the zero-operations V0 backend; the storage interface leaves room for PostgreSQL.
- Model calls use the OpenAI Responses API.
- Codex is a separate software-engineering delegate, not the scientific authority.
- Files and Git remain authoritative for papers and code; the database indexes state and provenance.

