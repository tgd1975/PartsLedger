---
id: TASK-058
title: One-line parser test walking IDEA-011 V1 output through /inventory-add's parser
status: paused
opened: 2026-05-14
effort: Small (<2h)
complexity: Medium
human-in-loop: No
epic: integration-followups
order: 2
prerequisites: [TASK-054]
---

## Description

Add a single integration test on the PartsLedger side that takes the
canonical CLI output of the resistor-reader extra (the V1 packaging
ships as `pip install partsledger[resistor-reader]`) and walks it
through `/inventory-add`'s argument parser, confirming the value
copies cleanly into a Workflow A invocation without manual reshaping.

This closes IDEA-012 Gap 9: the resistor reader and the skill path
share no code, but they share an interchange shape — the human-
readable string `1k 5%` (or `4.7k 1%`, etc.). The test asserts that
shape stays stable across both surfaces.

## Acceptance Criteria

- [ ] `tests/integration/test_resistor_reader_to_inventory_add.py`
      exists and passes.
- [ ] The test parameterises over the V1 fixture image set
      (`tests/fixtures/resistor-reader/`) — each fixture's expected
      decoded value round-trips through `/inventory-add`'s parser
      into the canonical INVENTORY.md row shape (`Part`, `Qty`,
      `Description`, `Notes`).
- [ ] A deliberately-malformed reader output surfaces a clear parse
      error in `/inventory-add`, not a silent miss.

## Test Plan

**Host tests (pytest)**:

- `tests/integration/test_resistor_reader_to_inventory_add.py` — the
  single test described above. Cover: each E-series resistor in the
  V1 fixture set; one malformed-output negative case.

## Prerequisites

- **TASK-054** — V1 packaging closes when the extra ships with a
  documented CLI output shape; this test pins that shape.

## Paused

- 2026-05-14: Waiting on TASK-054 (V1 packaging) to close. Authoring
  the test before the CLI output shape is fixed would freeze a draft
  format.

## Notes

This is a small integration test, not a re-implementation of the
parser. PartsLedger's resistor reader and `/inventory-add` are kept
deliberately decoupled — the test is the only thing that asserts
they speak the same string format.
