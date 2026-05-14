---
id: TASK-052
title: V1 — band reading + EIA classifier + orientation disambiguation via E-series check
status: open
opened: 2026-05-14
effort: Medium (2-8h)
complexity: Senior
human-in-loop: Support
epic: resistor-reader
order: 2
prerequisites: [TASK-051]
---

## Description

Second half of the V1 still-image pipeline from
[IDEA-011 § Rough approach #2](../../ideas/open/idea-011-resistor-color-band-detector.md#rough-approach).
Given a localised resistor body (from
[TASK-051](task-051-resistor-localisation-v1.md)), find the band
positions along the body axis, sample each band's dominant colour,
classify each band against the EIA colour palette, and decode the
result to a nominal resistance value with tolerance.

The orientation problem (which end is band 1?) is resolved by
trying both directions and keeping the one that decodes to a valid
E12 / E24 / E96 value; if both decode to valid E-series values, the
higher-precision series wins and confidence is reduced accordingly.
The decoder handles both 4-band and 5-band color codes.

Lives at `src/partsledger/resistor_reader/decode.py`. Public surface
is a single function consuming a `Candidate` from `localise.py` and
returning a decoded value plus tolerance plus per-band confidence
breakdown. Output values use the PartsLedger value-formatting
convention (`4k7`, `100R`, `1M`) so a copy-paste of the decoder
output works as `/inventory-add` input
([IDEA-011 open Q "Relationship to PartsLedger"](../../ideas/open/idea-011-resistor-color-band-detector.md#open-questions)).

The EIA palette and E-series tables are module-internal constants.
The decoder reads but does not write the colour-calibration profile
from [IDEA-013](../../ideas/open/idea-013-capture-setup-and-color-calibration.md);
profile-loading itself is the job of
[TASK-054](task-054-resistor-extra-packaging.md), this module just
takes already-corrected pixels as input.

## Acceptance Criteria

- [ ] `src/partsledger/resistor_reader/decode.py` exposes
      `decode_resistor(image, candidate) -> DecodedResistor` with
      fields `value`, `tolerance`, `bands`, `confidence`,
      `orientation_resolved` (bool).
- [ ] 1k 5%, 4.7k 5%, and 220 1% test resistors decode correctly
      under standard lighting on the fixture set.
- [ ] Ambiguous-orientation frames return the higher-E-series
      winner (E96 beats E24 beats E12) with a reduced confidence
      score.
- [ ] Both 4-band and 5-band color codes decode; a fixture for
      each is in the test set.
- [ ] Output values format as `4k7`, `100R`, `1M` per the
      PartsLedger schema — verified by a string-match test against
      a fixture ground-truth JSON.

## Test Plan

Host tests (pytest) against the fixture image set in
`tests/fixtures/resistor-reader/` extended with the
ground-truth-value sidecar JSONs:

- `tests/resistor_reader/test_decode.py` — feed each fixture
  through `localise.py` then `decode.py`, assert the decoded
  value-string matches the sidecar ground truth.
- Cover at minimum: 1k 5% (4-band), 4.7k 5% (4-band), 220 1%
  (5-band), one orientation-ambiguous case (e.g. 4k7 vs the
  invalid reverse decode), one near-miss case where two
  E-series interpretations both decode validly.

## Prerequisites

- **TASK-051** — supplies the `Candidate` type and the
  `locate_resistors` entry point this decoder consumes.

## Notes

Per [IDEA-011's open-Q closure on calibration](../../ideas/open/idea-011-resistor-color-band-detector.md#open-questions),
when no [IDEA-013](../../ideas/open/idea-013-capture-setup-and-color-calibration.md)
colour profile is available the decoder falls back to
white-balance-naive classification and the report surfaces this as
lower baseline confidence. The profile-loading itself is wired in
[TASK-054](task-054-resistor-extra-packaging.md); this module only
needs to expose a parameter that the caller can use to pass in a
correction matrix.
