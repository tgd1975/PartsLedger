---
name: bash-no-prompts
description: Write Bash commands that don't trigger unnecessary permission prompts. Use Read/Edit/Grep instead of head/tail/sed/awk/cat/echo; split chained commands (&&, ;, ||) into separate Bash calls; drop diagnostic suffixes like `; echo "EXIT=$?"`. The allowlist matches whole command strings — every mismatch costs the user attention.
---

# bash-no-prompts

The Bash permission allowlist matches the **whole command string**. A compound
like `git status && echo OK` does not match `Bash(git status:*)` because the
suffix changes the string. Every mismatch makes the user click an approve
button for no content reason. **This skill exists to make that click rate go
to zero on commands that don't genuinely need user attention.**

## Preflight (before every Bash call)

Scan the command you're about to send for these patterns, in order:

### 1. Forbidden primaries — switch to a dedicated tool

| You wrote | Use instead | Why |
|---|---|---|
| `head -N file`, `tail -N file` | `Read(file, offset, limit)` | Read is the documented tool |
| `sed -n A,Bp file` | `Read(file, offset=A, limit=B-A+1)` | same |
| `sed -i ...`, `awk ... > file` | `Edit` or `Write` | same |
| `cat file` (as display) | `Read(file)` | Read |
| `echo "$VAR"`, `echo "EXIT=$?"` | nothing — trust the doc; `Read(.envrc)` if you really need the value | echo-as-diagnostic is bash-as-poor-substitute |
| `grep -r pattern dir/` | `Grep` tool | dedicated tool |

**The one `cat` exception**: heredoc form (`cat <<'EOF' ... EOF`) inside
wrapper scripts (notably `/commit`) is **load-bearing** — that's writing
content to stdin of another command, not displaying a file. Don't flag it,
don't propose it for the deny list. Only the *display* use of `cat` is the
anti-pattern.

### 2. Shell chaining — split into separate Bash calls

Compound commands defeat the allowlist matcher even when each piece would be
individually allowed. Rewrite:

- `cmd1 && cmd2` → two Bash calls (in parallel if independent)
- `cmd1 ; cmd2` → two Bash calls
- `cmd1 || cmd2` → two Bash calls
- `{ cmd1; cmd2; }` → two Bash calls
- `for f in ...; do cmd; done` → loop in Python via Write+Read, not Bash

**Genuine pipe exception**: `git log --oneline | grep foo` is one operation
(stdout-of-A as stdin-of-B). Accept the prompt — rewriting it would mean
reimplementing the pipeline manually, which is worse.

**Pipe-into-trunc is NOT a genuine pipe**: `grep foo file | head -20` is the
single most common offence. The `| head -20` is output truncation, not a
real pipeline. **Drop the truncation; let the full output through.** Full
output is fine — token cost is negligible compared to the user's attention.

### 3. Diagnostic suffixes — never

Don't append `; echo "EXIT=$?"`, `&& echo OK`, `|| echo FAIL`, `; echo "---"`,
or similar diagnostic chains. They:

- Add nothing functionally — the Bash tool already reports exit codes and
  full stdout/stderr in its result.
- Defeat the matcher (compound command string).
- Embed `echo`, which is itself flagged.

Just run the command; trust the tool result.

### 4. Use the path form the allowlist registers

If a project allowlist has `Bash(python scripts/X.py:*)`, that matches the
**relative** invocation `python scripts/X.py ...` — not the absolute form
`python /home/.../scripts/X.py ...`. Default to the relative form for any
in-repo script.

## When the deny rule fires anyway

If the project has `deny` rules on `head`/`tail`/`sed`/`awk` and you hit one:

1. **Do not retry with another forbidden form.** Denied `head` → also denied
   `tail`. The user sees the loop.
2. **Was this output-truncation?** Drop the `| head -N` / `| tail -N` and
   re-run the primary command. The full output is fine — *that's the whole
   point of dropping the suffix*.
3. **Was this file-reading?** Switch to `Read` with `offset`/`limit`.
4. **Was this file-editing?** Switch to `Edit`.
5. **Was this a heredoc inside `/commit` or similar?** That's the cat
   exception above. If the wrapper script itself is the source of the
   denied command, surface that to the user — don't try to rewrite the
   wrapper from inside the Bash call.

## Quick mental check

Before any Bash call, run this one-liner in your head:

> *"Is this command something a known allowlist rule would match exactly?
> Or am I about to send a compound / forbidden-primary string that will
> bounce the user with a prompt for no content reason?"*

If the answer is "bounce", rewrite or split before sending. The user's
attention is the resource being protected — not Bash convenience.
