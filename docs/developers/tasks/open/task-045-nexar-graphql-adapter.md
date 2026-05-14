---
id: TASK-045
title: Implement src/partsledger/enrichment/nexar.py — OAuth + GraphQL supSearchMpn
status: open
opened: 2026-05-14
effort: Medium (2-8h)
complexity: Senior
human-in-loop: Clarification
epic: metadata-enrichment
order: 1
prerequisites: [TASK-022]
---

## Description

Bring up the bare HTTP/GraphQL transport against Nexar in isolation
(IDEA-008 Stage 1). New module `src/partsledger/enrichment/nexar.py`
performs OAuth client-credentials against Nexar's identity endpoint,
caches the bearer token in-memory for the session, then POSTs a single
GraphQL `supSearchMpn` query against the data endpoint and parses the
response into a `NexarPart` dataclass.

Credentials come from `$PL_NEXAR_CLIENT_ID` and `$PL_NEXAR_CLIENT_SECRET`
per the project env-var policy — never typed inline. The `NexarPart`
dataclass holds exactly the fields named in IDEA-008's
*Primary path — Nexar GraphQL API* table: `mpn`, `manufacturer`,
`datasheet_url`, `category_path`, `lifecycle_status`. The `bestImage`
field is explicitly **not** queried — IDEA-008's closed *Image upload*
question rules out image retention.

Secrets discipline mirrors IDEA-007's handling: the bearer token and
raw client-secret must be redacted in every log line, error message,
and stack trace. A failed auth logs *"auth failed against
<https://identity.nexar.com>"* — never the credential value.

This task is the standalone transport; no caching, no orchestrator,
no writer wiring yet. Those are TASK-046 and TASK-048.

## Acceptance Criteria

- [ ] `lookup_mpn("LM358N")` against live credentials returns a `NexarPart`
      with non-empty `datasheet_url`, `manufacturer`, and `category_path`.
- [ ] `lookup_mpn("XYZJUNK999")` returns `None` rather than raising.
- [ ] `lookup_mpn(...)` with `$PL_NEXAR_CLIENT_ID` unset raises a clean
      `EnrichmentDisabledError` — callers can `except` it without
      parsing a traceback.
- [ ] Induced 401 logs the redacted form; no credential string appears
      anywhere in captured logs.
- [ ] Bearer token is cached in-memory for the session and reused
      across successive `lookup_mpn` calls.

## Test Plan

**Host tests (pytest)** under `tests/enrichment/test_nexar.py`:

- Mock the OAuth and GraphQL HTTP endpoints with `responses` or
  `requests-mock`. Cover: successful auth + lookup, 401 auth-fail
  surfacing a redacted error, junk-MPN returning `None`, missing
  client-ID raising `EnrichmentDisabledError`, secret redaction in log
  capture.
- Token caching: assert a second `lookup_mpn` call within the same
  session does not re-hit the identity endpoint.

**Manual integration test** against live Nexar credentials:
`lookup_mpn("LM358N")` returns a populated `NexarPart` whose
`datasheet_url` resolves to a TI PDF.

## Prerequisites

- **TASK-022** — `src/` layout is in place so `src/partsledger/enrichment/`
  is a valid package destination.

## Notes

- Env-var refs: `$PL_NEXAR_CLIENT_ID`, `$PL_NEXAR_CLIENT_SECRET` (see
  `.envrc.example`).
- `requests` is already declared in `pyproject.toml`; no new runtime
  dep.
- Human-in-loop is `Clarification`: the user may need to grant or
  rotate Nexar credentials before live testing. The implementation
  itself is unambiguous.
- Rate-limit considerations are deferred to the dispatch layer
  (TASK-049, `max_workers=1`); this module does not retry on 429.
