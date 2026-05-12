---
name: check-tool
description: Check whether a CLI tool or package is available; if not, ask the user to install it before continuing
---

# check-tool

Use this skill whenever you are about to run a command or import a library and you are
not certain it is installed. **Do not attempt workarounds or reimplement the tool's
logic.** One check, then ask.

## When to invoke

Invoke proactively before:

- Running a CLI tool that may not be globally installed (e.g. `markdownlint`, `clang-tidy`,
  `jq`, `ajv`, `jsonschema`)
- Importing a Python package that is not part of the standard library
- Using an `npx`-runnable tool when `node_modules` may not be present

## Steps

1. **Check availability** using the lightest possible probe:

   | Tool type | Probe command |
   |-----------|---------------|
   | CLI binary | `which <tool> 2>/dev/null \|\| command -v <tool> 2>/dev/null` |
   | Python package | `python -c "import <pkg>" 2>/dev/null` (exit 0 = present) |
   | npm package (global) | `npm list -g --depth=0 <pkg> 2>/dev/null` |
   | npx-runnable | `npx --no-install <tool> --version 2>/dev/null` |

2. **If found:** proceed silently — do not mention the check.

3. **If not found:** stop immediately and ask the user using this exact message pattern:

   > I need `<tool>` to continue but it isn't installed.
   > Can you install it?
   >
   > **Suggested install command:**
>
   > ```
   > <install command>
   > ```
   >
   > Let me know when it's ready and I'll continue.

   Then **wait** — do not attempt alternatives, do not reimplement the logic in shell or
   Python, do not proceed with the task.

1. **After the user confirms:** re-run the probe to verify, then continue.

## Install command hints

| Tool | Suggested install |
|------|-------------------|
| `jsonschema` (Python) | `pip install -r requirements.txt` (declared in project `requirements.txt`) |
| `markdownlint-cli` | `npm install -g markdownlint-cli` |
| `clang-tidy` | `sudo apt install clang-tidy` (Ubuntu) / install via LLVM (Windows) |
| `jq` | `sudo apt install jq` (Ubuntu) / `winget install jqlang.jq` (Windows) |
| `ajv-cli` | `npm install -g ajv-cli` |
| `mmdc` (Mermaid) | `npm install -g @mermaid-js/mermaid-cli` |

For anything not listed, suggest the most obvious package manager command for the
current OS (check `/os-context` if unsure).

## What NOT to do

- Do not retry with `npx`, a full path, or a venv as a fallback after the first check fails
- Do not reimplement the missing tool's logic in Python or shell
- Do not silently skip the validation step
- Do not proceed with the task until the user confirms the tool is installed
