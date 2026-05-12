---
name: os-context
description: Detect the current OS and print shell syntax reminders for Windows vs Ubuntu
---

# os-context

Detect the current OS and remind yourself of the correct shell/CLI syntax to use.

## Detection — no shell command needed

The system prompt always contains a `Platform:` field. Read it directly:

- `Platform: win32` → **Windows 11 (Git Bash / MSYS2)**
- `Platform: linux` → **Ubuntu / Linux**
- `Platform: darwin` → **macOS**

Only fall back to running `uname -s && uname -m` if the `Platform:` field is absent or ambiguous.

## Syntax rules by platform

**Windows 11 (Git Bash / MSYS2)**

- Shell is bash, but underlying OS is Windows 11
- Use forward slashes in paths: `C:/Users/...`
- Unix tools from Git Bash work: `ls`, `grep`, `cat`, etc.
- Avoid `cmd.exe` syntax: no `dir`, `type`, `copy`, `del`, no backslashes
- Use `wsl` prefix only when a command truly requires the Linux kernel
- PlatformIO config files may need Windows-style absolute paths

**Ubuntu / Linux**

- Standard bash — everything works as expected
- `/dev/null`, `apt`, package paths, symlinks all native

## Output

Print a one-line context summary:

```
OS: Windows 11 (Git Bash/MSYS2) — using Unix shell syntax, Windows absolute paths where needed.
```

or

```
OS: Ubuntu Linux — using standard bash syntax.
```

Then apply the correct syntax for all subsequent shell commands in this session.
