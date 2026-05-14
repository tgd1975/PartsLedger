---
id: TASK-042
title: Implement src/partsledger/recognition/vlm.py — OpenAI-compatible REST adapter
status: open
opened: 2026-05-14
effort: Large (8-24h)
complexity: Senior
human-in-loop: No
epic: visual-recognition
order: 4
prerequisites: [TASK-022]
---

## Description

IDEA-007 Stage 3 — the single OpenAI-compatible REST adapter that speaks
to whatever VLM endpoint `$PL_VLM_BASE_URL` resolves to. Default is
Claude Opus 4.7 Vision via the Anthropic API (per CLAUDE.md and IDEA-007 §
Maker-facing config). The same adapter works for Pixtral via Mistral /
Ollama / vLLM without code changes — provider swap is env-var-only per
IDEA-007 § Why Pattern A.

New module `src/partsledger/recognition/vlm.py` reads `$PL_VLM_BASE_URL`,
`$PL_VLM_MODEL`, and `$PL_VLM_API_KEY` at module init and exposes
`identify(image, neighbour_hints=None) -> VLMVerdict`. The verdict is one
of three structured variants per IDEA-007 § Where the VLM still earns its
keep:

- `HedgedID(label, marking, hedge)` — single-best identification, hedge
  phrasing enforced.
- `NeedsReframe(hint)` — reframe required; hint tokenised into one of the
  seven IDEA-006 § Recognition-state hints families, or collapsed to a
  generic *"image unclear — recompose and retry"*.
- `NoIdea()` — genuine cold-start; no retry.

Implementation requirements:

1. **Structured-output enforcement** — request `response_format:
   {"type": "json_schema", ...}` when the provider supports it; fall back
   to a parser + retry loop (cap of 2 retries, configurable) when output
   is non-conformant.
2. **Hedge-grammar parser** — rejects identifications that don't start
   with a hedging adverb (`likely`, `probably`, `appears to be`) and
   rejects the forbidden modals `must / always / never` per IDEA-007 §
   Hedge-language enforcement.
3. **Secrets redaction** — `$PL_VLM_API_KEY` MUST be redacted in every
   log line, error pass-through, and stack trace per IDEA-007 § Secrets
   handling. The adapter never echoes the key to stdout / stderr at
   startup. A failed auth is logged as *"auth failed against
   $PL_VLM_BASE_URL"*, never with the bearer value.

The adapter never imports a vendor-specific SDK (no `anthropic`,
`mistralai`, etc. as dependencies) — the OpenAI-compatible REST shape is
the only transport.

## Acceptance Criteria

- [ ] `identify()` returns the correct variant for each of three mocked HTTP responses (hedged ID, needs-reframe, no-idea).
- [ ] An identification missing the hedging adverb triggers a retry; the third failure surfaces as `NoIdea()`.
- [ ] `NeedsReframe(hint)` hints tokenise into one of the seven IDEA-006 families, or collapse to the generic fallback string.
- [ ] An induced 401 from the provider redacts the bearer token in the logged error (no `sk-…` substring appears in captured log output).
- [ ] No vendor SDK appears in the module's imports — only `requests` (or `httpx`) + stdlib + numpy / PIL.
- [ ] The module never prints the API key value at startup; verbose mode at most prints presence + length.

## Test Plan

**Host tests** (pytest):

- Add `tests/recognition/test_vlm.py`.
- Mock HTTP transport (e.g. `responses` or `respx`).
- Cover: each of three verdict variants parsed correctly; hedge-grammar
  rejection + retry; retry cap of 2; secrets-redaction in logged errors
  on a 401; structured-output JSON-schema path; parser-fallback path.

## Prerequisites

- **TASK-022** — Python package skeleton with `requests`/`httpx`
  available; this task is the first network-touching module.

## Sizing rationale

VLM adapter is one coherent contract spanning auth, request shaping,
three structured-verdict parsers, retry, and secrets-redaction; partial
scaffolds leave the verdict shape unstable for downstream callers.

## Notes

`$PL_VLM_BASE_URL`, `$PL_VLM_MODEL`, `$PL_VLM_API_KEY` are the only env
vars this module reads. Default values come from `.envrc` (template at
`.envrc.example`) — IDEA-007 § Maker-facing config shows the
Anthropic / Mistral / Ollama variants.
