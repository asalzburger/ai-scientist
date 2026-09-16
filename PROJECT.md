# AI Scientist — Project Charter

## Product statement

Create a persistent AI scientist that behaves like a bounded member of a research team: it knows its responsibilities, maintains tasks and projects, prepares for meetings, runs reproducible studies, drafts communication and papers, and delegates software engineering to Codex.

## Current milestone: V0.1 Communications

V0 proves the core operating model before adding broad autonomy.

The immediate focus is a usable, project-neutral scientist workspace. NODD remains
an optional example; research execution is deferred while the local workflow is built.

Implemented usability slice:

- Initialize an empty workspace, optionally seeding NODD with `init --example`.
- Create, list, and update tasks, including completion and explicit next actions.
- Save user-authored notes and decisions and include them in future chat context.
- Persist each record save and its audit event atomically.
- Use a generic researcher identity by default.

Chat remains advisory and does not persist conversations or mutate workspace state.
General natural-language state updates, interactive sessions, and provider-independent
model adapters remain future work.

The current priority is communication capability, before detector research workflows.
Implemented modules provide model-assisted email drafts, reply threading, SMTP
delivery, read-only IMAP/JMAP import, local contacts, event drafts, bounded recurrence,
iCalendar invitations, CalDAV availability and approved event creation, and an embedded
read-only review dashboard. Integration protocols run in-process without connector services.

Consequential writes now use durable, expiring, single-use approvals tied to exact
payloads and accounts. State changes and approval transitions are audited atomically.
Account connectivity remains to be verified against the user's chosen providers;
tests exercise protocol boundaries offline and perform no live delivery.

Communication habits start with selective quick questions in chat, longer asynchronous
explanations by email, and daily priority lists focused on forward progress. Typed
human feedback persists and is supplied to subsequent model calls so choices can
improve with use. This is feedback-informed reasoning, not automatic model training
or policy changes. Daily briefings are saved drafts; no schedule, ping quota, or
automatic delivery is configured. The scientist will use a dedicated account, with
credentials supplied later.

### In scope

- Scientist identity and policy configuration
- Typed projects, tasks, experiments, papers, meetings, people, claims, and evidence
- SQLite persistence outside model context
- Daily-status context assembly
- Responses API chat entry point
- Approval gate for consequential actions
- A bounded Codex delegation adapter
- CLI and unit tests
- Email/calendar modules and human-reviewed external writes
- Local browser review of drafts and approvals

### Out of scope

- Autonomous email sending
- Unapproved calendar mutation
- Mattermost notifications, Zoom connectivity, OAuth setup, and web editing
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
| V0.1 | In-process email/calendar, contacts, durable approvals, local review dashboard |
| V1 | Literature, GitHub, Drive, notebook, citations |
| V2 | Codex delegation, containers, experiment execution and result ingestion |
| V3 | Mattermost notifications, meeting preparation, and Zoom integration |
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
