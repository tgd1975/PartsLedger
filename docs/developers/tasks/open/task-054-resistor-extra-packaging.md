---
id: TASK-054
title: V1 — package as partsledger[resistor-reader] extra with CLI entry-point
status: open
opened: 2026-05-14
effort: Small (<2h)
complexity: Medium
human-in-loop: No
epic: resistor-reader
order: 4
prerequisites: [TASK-052, TASK-053]
---

## Description

Wire the V1 pipeline into PartsLedger's distribution so the maker
installs and uses it without leaving the standard `pip` path. Per
the
[IDEA-011 open-Q closure on packaging](../../ideas/open/idea-011-resistor-color-band-detector.md#open-questions),
the decoder ships as an optional extra
(`pip install partsledger[resistor-reader]`) — same source tree,
one distribution, heavier CV deps stay out of the bare-bones
install.

Three pieces:

1. **Extra declaration** in `pyproject.toml` under
   `[project.optional-dependencies]` — add a `resistor-reader`
   key listing `opencv-python` (or `opencv-contrib-python` if
   needed for any specific feature) plus any module-level deps
   the V1 modules pull in. This rides on the extras mechanism
   established by [TASK-029](task-029-pyproject-extras.md).
2. **CLI entry-point** at
   `src/partsledger/resistor_reader/__main__.py` and the
   `[project.scripts]` entry
   `partsledger-resistor-reader = "partsledger.resistor_reader.__main__:main"`.
   Invocation: `partsledger-resistor-reader <image>` (or
   `python -m partsledger.resistor_reader <image>`). The CLI
   prints the decoded value(s) plus, when the input is a
   multi-resistor frame, the uniformity report. Output is plain
   text by default; a `--json` flag emits a structured form for
   piping into [IDEA-005](../../ideas/open/idea-005-skill-path-today.md)'s
   `/inventory-add`.
3. **Calibration-profile load**. Per
   [IDEA-013 § Consumers](../../ideas/open/idea-013-capture-setup-and-color-calibration.md#consumers)
   the resistor decoder is a consumer of the colour profile that
   IDEA-013's `calibrate` step produces. Look for
   `$PL_INVENTORY_PATH/.calibration/color_profile.toml` first; if
   absent, fall back to the user-config dir
   (`~/.config/partsledger/calibration/color_profile.toml` on
   Linux); if still absent, fall back to white-balance-naive
   decoding and surface a one-line note in the CLI output
   ("no calibration profile — confidence baseline reduced"). The
   maker never sees the file paths themselves in the output —
   "no calibration profile" is the user-facing message.

OpenCV internals (HSV ranges, contour thresholds, profile-file
schema, fall-back logic) must not surface in `--help` or error
messages. The maker-facing surface is one CLI command, one
optional `--json`, one optional `--calibrate <profile-path>`
override.

## Acceptance Criteria

- [ ] `pip install partsledger[resistor-reader]` succeeds in a
      fresh venv and pulls the CV deps not present in the bare
      `pip install partsledger`.
- [ ] `partsledger-resistor-reader <fixture-image>` prints the
      decoded value in PartsLedger schema format (`4k7`, `100R`)
      for the canonical single-resistor fixture.
- [ ] `--json` emits a structured form whose keys match the
      `DecodedResistor` / `UniformityReport` fields.
- [ ] When `$PL_INVENTORY_PATH/.calibration/color_profile.toml`
      exists, the CLI loads it and the report does not carry the
      "no calibration profile" note.
- [ ] When no profile is found in either location, the CLI still
      decodes successfully and prints the "no calibration
      profile" note.
- [ ] No OpenCV detail (HSV ranges, thresholds, internal file
      paths) appears in `--help`, normal output, or error
      messages.

## Test Plan

Host tests (pytest) against fixtures in
`tests/fixtures/resistor-reader/`:

- `tests/resistor_reader/test_cli.py` — invoke the entry point
  via `subprocess.run([sys.executable, "-m",
  "partsledger.resistor_reader", fixture_path])` and assert on
  stdout for the canonical fixtures.
- Cover: single-resistor fixture (text output), multi-resistor
  fixture with `--json` flag (parse stdout, assert
  `uniform` field), no-profile run (assert the "no calibration
  profile" note appears), profile-present run (assert the note
  is absent — fixture profile lives at
  `tests/fixtures/resistor-reader/calibration/color_profile.toml`).
- Manual smoke test: in a fresh venv,
  `pip install -e .[resistor-reader]` then
  `partsledger-resistor-reader tests/fixtures/resistor-reader/single-1k.jpg`
  — confirm the script is on `$PATH` and prints `1k`.

## Prerequisites

- **TASK-052** — supplies the `decode_resistor` function the CLI
  invokes per candidate.
- **TASK-053** — supplies the `check_uniformity` function the CLI
  invokes on multi-resistor frames.

## Notes

Profile-storage location follows
[IDEA-013's open-question lean toward option (c)](../../ideas/open/idea-013-capture-setup-and-color-calibration.md#open-questions):
inventory-local first, user-config dir as fallback. The
inventory-local path uses `$PL_INVENTORY_PATH` so off-bench users
without a PartsLedger inventory still get the user-config dir as
a working fallback. No profile-writing happens here — that
remains [IDEA-013](../../ideas/open/idea-013-capture-setup-and-color-calibration.md)'s
job.
