---
name: update-scripts-readme
description: Auto-update scripts/README.md when scripts are added, changed, or removed
---

# update-scripts-readme

Automatically updates the `scripts/README.md` documentation to reflect the current state of the scripts folder by running the `update_scripts_readme.py` script.

## Invocation

The user invokes this as `/update-scripts-readme` with no arguments.

## Steps

1. **Run the update script**: Execute `python3 scripts/update_scripts_readme.py`
2. **Report results**: Show the output from the script execution
3. **Verify success**: Confirm that the README was updated and markdown lint passed

## Implementation

The skill simply runs the existing `scripts/update_scripts_readme.py` script which:

- Scans all Python and shell scripts in the `scripts/` directory
- Extracts documentation from docstrings and comments
- Generates a comprehensive README.md with:
  - Table of all scripts with purpose and usage
  - Detailed sections for each script
  - Proper markdown formatting
- Validates the generated markdown with markdownlint-cli2

## Example Output

```
🔍 Scanning scripts directory...
📝 Updated /home/user/project/scripts/README.md
🔍 Validating markdown...
✅ Markdown lint: PASSED
```

## Notes

- The script automatically handles all Python (.py) and shell (.sh) scripts
- Scripts must have proper docstrings/comments to be included in documentation
- The generated README follows the same structure as the original manual documentation
- Do not commit automatically - let the user review the changes first
