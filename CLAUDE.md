# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

ArchCorp Cenário 4 is an academic Enterprise Systems Architecture project (Projeto Aplicado). It's an executable prototype demonstrating integration between CRM, Contracts, Finance, Support, and Workflow systems. The architecture follows a fixed ADR: a pragmatic SOA delivered initially as a modular monolith, using REST for immediate responses and outbox-persisted events for async effects.

**Read `AGENT.md` before making changes** — it is the authoritative, detailed rulebook for this repo (module boundaries, data ownership, integration contracts, reliability, security, observability, testing, and scope restrictions). This CLAUDE.md summarizes the operational parts; `AGENT.md` is the source of truth when the two disagree.

## Commands

Local dev (Windows/PowerShell), from repo root:

```powershell
python -m venv .venv
./.venv/Scripts/pip install -r requirements-dev.txt
$env:PYTHONPATH = "src"
./.venv/Scripts/pytest
```

Run a single test file or test:

```powershell
./.venv/Scripts/pytest tests/test_flows.py
./.venv/Scripts/pytest tests/test_flows.py::test_nome_da_funcao -v
```

Run the full stack (API + Postgres + RabbitMQ) via Docker:

```powershell
docker compose up --build
```
API: `http://localhost:8000`, Swagger UI: `http://localhost:8000/docs`, RabbitMQ management: `http://localhost:15672` (guest/guest, local only).

Run the end-to-end demo script against a running stack:

```powershell
./scripts/demo.ps1
```

Auth for manual/demo calls: `Authorization: Bearer demo-admin` (also `demo-commercial`, `demo-contracts`, `demo-finance`, `demo-support`, `demo-operations` — see `src/archcorp/security.py` for the role map). These are local simulated tokens standing in for a real OIDC provider.

## Architecture

### Bounded contexts

Code lives under `src/archcorp/<context>/`, one package per bounded context: `crm`, `contracts`, `finance`, `support`, `workflow`, `integration`, plus shared `infrastructure`. Each context owns its data (see the ownership table in `AGENT.md`) and typically contains:

- `models.py` — SQLAlchemy models, private to the context
- `service.py` — use cases / application logic (the hexagon's inside)
- `public.py` — the only interface other contexts may depend on (e.g. `src/archcorp/contracts/public.py` defines `ContractEntitlementPort`, a `Protocol`)

**Cross-context model imports are forbidden and mechanically enforced**: `tests/test_contracts_and_architecture.py::test_modulos_de_negocio_nao_importam_models_de_outro_contexto` walks the AST of every business-module file and fails the build if one context imports another context's `models`. Cross-context calls must go through a `public.py` port or through events — never direct table/model access, even though everything currently shares one Postgres instance.

`src/archcorp/main.py` is the composition root: it wires services together (`CustomerService`, `ContractService`, `TicketService`), builds the `EventDispatcher` with a static `event_type -> [(consumer, handler), ...]` map, and defines every FastAPI route. Route handlers stay thin — they translate HTTP <-> service calls and set correlation/idempotency headers; business rules live in each context's `service.py`.

### Integration pattern (outbox/inbox)

- Mutations that must have async effects write an `OutboxEvent` in the same transaction (`integration/service.py::enqueue`).
- `POST /api/v1/integration/outbox/dispatch` (or `EventDispatcher.dispatch_pending`) drains `PENDING` events, invokes registered handlers per event type, records an `InboxEvent` per `(event_id, consumer)` pair for idempotent consumption, and optionally publishes to RabbitMQ if `RABBITMQ_URL` is configured.
- Failed handlers increment `attempts`; after `settings.retry_limit` the event becomes `FAILED` and is exposed via `GET /api/v1/integration/failures`, reprocessable via `POST /api/v1/integration/failures/{eventId}/reprocess`.
- Every event envelope carries `eventId`, `eventType`, `eventVersion`, `occurredAt`, `correlationId`, `causationId`, `producer`, `payload` (see `docs/events/asyncapi.yaml`).
- Mutating HTTP endpoints that can be retried accept an `Idempotency-Key` header and return `Idempotency-Replayed: true|false`.
- `X-Correlation-ID` is generated per-request if absent (`main.py` middleware), propagated through logs, audit entries, and events, and queryable via `GET /api/v1/operations/{correlationId}`.

### Contract-code sync (important, mechanically enforced)

`tests/test_contracts_and_architecture.py::test_openapi_salvo_corresponde_a_aplicacao_e_documenta_exemplos` asserts `docs/api/openapi.yaml` (loaded via YAML) equals `app.openapi()` byte-for-byte in structure. **Any route/schema change in `main.py` or `schemas.py` requires regenerating and committing `docs/api/openapi.yaml` in the same change**, or this test fails. There's no automated generation script for this in the repo — update the YAML by hand (or script a dump of `app.openapi()`) to match.

Similarly, `docs/events/asyncapi.yaml` is checked for the three required channels (`contractActivated`, `ticketOpened`, `customerUpdated`) and required envelope fields — keep it in sync with any event schema change.

### Config and cross-cutting

- `config.py` — `pydantic-settings` `Settings` (env-driven: `DATABASE_URL`, `RABBITMQ_URL`, `RETRY_LIMIT`, etc.), read via `.env` locally.
- `security.py` — `require_roles(*roles)` FastAPI dependency; simulated bearer tokens map to role sets (replace with real OIDC without changing the dependency's shape).
- `observability.py` — structured logger, `correlation_id_var` (contextvar), Prometheus-style counters exposed at `GET /metrics`, `metrics_middleware`.
- `infrastructure/db.py` — SQLAlchemy engine/session/`Base`, shared by all contexts (single Postgres instance in this prototype, per the ADR).

## Testing conventions

- `tests/conftest.py` forces `DATABASE_URL` to a local SQLite file (`./tmp/test-archcorp.db`) and disables RabbitMQ before importing the app; the `clean_database` fixture drops/recreates all tables per test.
- `client` fixture is a `TestClient` over the real `app`; `admin_headers`/`integrated_contract` fixtures set up a customer+draft contract for reuse.
- `AGENT.md` requires tests proportional to risk per change (unit, integration, contract, end-to-end for the 3 mandatory flows, and failure/retry/timeout scenarios), and a regression test for every bug fix.

## Non-negotiable constraints (from AGENT.md)

- Business documentation, decisions, and commit/PR messages in Portuguese (Brazil); code identifiers, endpoints, and API fields in English.
- Don't replace the 5 external systems with full implementations, introduce Kubernetes/service mesh/multiple physical databases/microservices decomposition, or use a shared database as a shortcut between contexts — none of this without an explicit requirement and a new ADR.
- Any structural architectural decision needs a new ADR under `docs/adr/` rather than silently rewriting an accepted one.
- Never treat assumptions about the (fictional) organization as facts — flag them as premises to validate.
- The three flows in `AGENT.md` ("Fluxos mínimos que não podem regredir") must not regress: CRM draft creation without re-registration; contract activation triggering billing + onboarding via event without duplication; support ticket creation checking contract/SLA and starting a resolution process.

## Key docs map

- `docs/REQUISITOS.md`, `docs/VISAO_NEGOCIO.md` — requirements and business view
- `docs/arquitetura/AS_IS.md`, `docs/arquitetura/TO_BE.md`, `docs/adr/ADR-001-integracao-empresa-de-servicos.md` — architecture and the governing ADR
- `docs/INTEGRACOES.md`, `docs/EXEMPLOS_API.md`, `docs/api/openapi.yaml`, `docs/events/asyncapi.yaml` — integration contracts
- `docs/MATRIZ_RASTREABILIDADE.md`, `docs/BACKLOG_TASKS_SUBTASKS.md` — requirement-to-implementation traceability
- `docs/ROTEIRO_DEMONSTRACAO.md`, `docs/EVIDENCIAS_VALIDACAO.md` — demo script and validation evidence
