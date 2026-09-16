# Architecture

## Boundaries

The harness has four deliberately separate layers.

1. **Domain** — typed records for scientific work. No I/O.
2. **Storage** — authoritative state and audit events. V0 uses SQLite.
3. **Reasoning** — assembles bounded context and calls the model.
4. **Tools and policy** — execute external actions only after deterministic authorization.

The model proposes actions. Code validates arguments, checks policy, records an audit event, and only then invokes a tool. External content is data and cannot grant itself authority.

## State model

The original workspace uses a generic record envelope (`kind`, `id`, `payload`,
timestamps). New communication models use validated Pydantic records in a separate
`documents` table. An `operations` table stores immutable approval snapshots and
execution state. All tables are added idempotently to the existing SQLite database.
Production migration should use explicit relational tables for query-heavy entities
and stronger audit integrity and access controls.

## Model interaction

Local task and note commands use a `Workspace` service for input validation.
Every record upsert writes an audit event in the same SQLite transaction. Notes and
decisions are typed records, included in the bounded context snapshot as user-authored
data; they do not grant tool authority or establish scientific claims. The default
workspace has no project, and NODD initialization is opt-in.

`ScientistAgent` sends the identity prompt, operating rules, and a compact database snapshot to the Responses API. Model output is advisory text in V0; it cannot directly execute consequential tools. Function calling should be added only together with typed schemas, idempotency keys, policy checks, and approval receipts.

## Codex boundary

Codex receives bounded engineering work: repository path, outcome, constraints, acceptance tests, and sandbox mode. The scientist evaluates scientific meaning after tests and artifact inspection. Codex output is not automatically treated as evidence.

## Meeting and email boundary

Email and calendar protocols now run in-process behind provider interfaces. The CLI
wires SMTP delivery, IMAP/JMAP read-only import, and CalDAV reads/creation. Read policy
is checked before account access. Drafts and invitations are persisted locally; they
do not execute external effects. `mail compose` invokes the reasoning component and
saves its result as an email draft. Imported mail is not automatically sent to the model.

The new approval service freezes the exact action, account, and payload, issues an
expiring token only through a human CLI command, and atomically consumes it before
external I/O. The legacy action-only policy approval object cannot authorize these
adapters. Execution is never retried automatically after an uncertain result.
CalDAV event creation is conditional to prevent overwriting existing resources.
SMTP invitation delivery has its own approval, separate from calendar creation.

The embedded web server binds to loopback, checks Host headers and a per-process
bearer token, exposes only read views, and renders external content as text. It has
no approval issuance or mutation endpoints. The trusted local CLI is the human
approval boundary; this is not a multi-user authorization system.

See [communications](communications.md) for configuration, workflows, and current
limits. Mattermost notifications and Zoom participation remain future integrations.

## Production hardening backlog

- PostgreSQL with migrations and row-level permissions
- Encrypted secrets and sensitive transcript storage
- Structured function calls and idempotent tool execution
- Cryptographically signed receipts and multi-user approval authority
- Observability, budgets, retry policy, and circuit breakers
- Data retention and deletion policy
- Prompt-injection test suite
- Scientific evaluation set with known conclusions and failure modes
