# Architecture Decision Records

This folder is the decision log for PartsLedger. Each file is one
record of one decision: why it was taken, what it commits us to, and
what it costs.

## What an ADR is in this project

An ADR (Architecture Decision Record) is a **short, immutable note**
describing a single architectural decision and its rationale, in the
four-section format popularised by Michael Nygard's
[original 2011 memo](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).
The format here is intentionally minimal:

- **Context** — the constraint, problem, or trade-off the decision
  addresses. Two or three sentences.
- **Decision** — what was decided. One declarative paragraph.
- **Consequences** — what this commits us to (pro and con), and which
  downstream things become easier or harder.
- **Status** — `Accepted`, `Superseded by ADR-NNNN`, or `Deprecated`.
- **See also** — a link to the dossier section that owns the depth.

The dossier
([`docs/developers/ideas/open/idea-001-partsledger-concept.md`](../../ideas/open/idea-001-partsledger-concept.md))
remains authoritative for the *details* of every decision. ADRs are
the **index**: read the ADR to understand which constraints are
load-bearing; follow the link to the dossier when you need the full
argument.

## How to add an ADR

1. Pick the next free number (`docs/developers/adr/` files are named
   `NNNN-<kebab-case-summary>.md`).
2. Copy [`0000-template.md`](0000-template.md) — the maintained
   blank ADR — and fill in each section. (Alternatively, copy the
   structure of an existing accepted ADR.)
3. Frontmatter: `id`, `title`, `status`, `date` (ISO-8601), `dossier-section` (path + anchor when applicable).
4. Append a line to the index in this file under the matching section.
5. Run `/commit` per the project's commit policy.

## How to supersede an ADR

ADRs are immutable once `Accepted`. A revisit lands as a **new** ADR.
The new ADR's frontmatter carries `supersedes: ADR-NNNN`; the prior
ADR's status is updated to `Superseded by ADR-NNNN` (the only
permitted edit to an accepted ADR). Never edit the prior ADR's body —
the original reasoning stays as historical record.

## Index

### Accepted

(none yet)

### Superseded

(none yet)

### Deprecated

(none yet)
