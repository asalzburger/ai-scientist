# Architecture

## Boundaries

The harness has four deliberately separate layers.

1. **Domain** — typed records for scientific work. No I/O.
2. **Storage** — authoritative state and audit events. V0 uses SQLite.
3. **Reasoning** — assembles bounded context and calls the model.
4. **Tools and policy** — execute external actions only after deterministic authorization.

The model proposes actions. Code validates arguments, checks policy, records an audit event, and only then invokes a tool. External content is data and cannot grant itself authority.

## State model

The V0 store uses a generic record envelope (`kind`, `id`, `payload`, timestamps) so schemas can evolve quickly. Domain dataclasses validate known objects before insertion. Production migration should use explicit relational tables for query-heavy entities, immutable audit storage, and PostgreSQL row-level access controls.

## Model interaction

`ScientistAgent` sends the identity prompt, operating rules, and a compact database snapshot to the Responses API. Model output is advisory text in V0; it cannot directly execute consequential tools. Function calling should be added only together with typed schemas, idempotency keys, policy checks, and approval receipts.

## Codex boundary

Codex receives bounded engineering work: repository path, outcome, constraints, acceptance tests, and sandbox mode. The scientist evaluates scientific meaning after tests and artifact inspection. Codex output is not automatically treated as evidence.

## Meeting and email boundary

Later integrations should ingest calendar metadata, meeting transcripts, and email through provider adapters. Default behavior is read, summarize, extract actions, and draft. Sending, calendar mutation, joining meetings, recording, and speaking require explicit approval and applicable participant consent.

## Production hardening backlog

- PostgreSQL with migrations and row-level permissions
- Encrypted secrets and sensitive transcript storage
- Structured function calls and idempotent tool execution
- Signed, expiring approval receipts
- Observability, budgets, retry policy, and circuit breakers
- Data retention and deletion policy
- Prompt-injection test suite
- Scientific evaluation set with known conclusions and failure modes

