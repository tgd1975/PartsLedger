#!/usr/bin/env python3
"""
Automatically update scripts/README.md based on current scripts in the folder.

This script scans all executable files in the scripts/ directory, extracts
documentation from their docstrings/comments, and regenerates the README.md
with up-to-date information about all available scripts.

Usage: python3 scripts/update_scripts_readme.py
"""

import os
import re
import subprocess
from pathlib import Path

def extract_python_docstring(file_path):
    """Extract module docstring from Python script."""
    try:
        content = file_path.read_text(encoding='utf-8')
        # Match triple-quoted docstring at the beginning
        match = re.search(r'"""(.*?)"""', content, re.DOTALL)
        if match:
            return match.group(1).strip()
        match = re.search(r"'''(.*?)'''", content, re.DOTALL)
        if match:
            return match.group(1).strip()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return None

def extract_shell_comments(file_path):
    """Extract comments from shell script."""
    try:
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')
        comments = []
        
        # Skip shebang line
        for line in lines[1:15]:  # Check more lines after shebang
            stripped = line.strip()
            if stripped.startswith('#') and not stripped.startswith('##'):
                # Remove leading # and strip
                comment = stripped[1:].strip()
                if comment:  # Skip empty comments
                    comments.append(comment)
            elif stripped and not stripped.startswith('#'):
                break  # Stop at first non-comment line
                
        if comments:
            # Return first comment as purpose, look for usage in comments
            purpose = comments[0]
            usage = None
            for comment in comments[1:]:
                if 'usage:' in comment.lower():
                    usage = comment.split('usage:', 1)[1].strip() if len(comment.split('usage:', 1)) > 1 else None
                    break
            return purpose, usage
        return None, None
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return None, None

def get_script_info(file_path):
    """Extract purpose and usage from script documentation."""
    if file_path.suffix == '.py':
        doc = extract_python_docstring(file_path)
        if not doc:
            return None, None
        
        # Split into purpose (first sentence) and usage (rest or specific usage patterns)
        lines = doc.split('\n')
        first_line = lines[0].strip() if lines else ''
        
        # Look for usage patterns
        usage = None
        for line in lines:
            if 'usage:' in line.lower():
                parts = line.split('usage:', 1)
                if len(parts) > 1:
                    usage = parts[1].strip()
                break
        
        if not usage:
            # Try to find command-line patterns
            for line in lines:
                if re.search(r'python3?\s+\S+', line) or re.search(r'\./\S+', line):
                    usage = line.strip()
                    break
        
        return first_line or doc.split('.')[0] + '.' if '.' in doc else doc, usage
    
    elif file_path.suffix in ['.sh', '']:  # .sh or no extension
        return extract_shell_comments(file_path)
    
    return None, None

def generate_readme(scripts_dir):
    """Generate updated README.md content."""
    scripts = []
    
    # Get all Python and shell scripts in scripts directory
    for file_path in sorted(scripts_dir.glob('*')):
        if file_path.is_file() and (file_path.suffix == '.py' or file_path.suffix == '.sh' or (file_path.suffix == '' and file_path.stat().st_mode & 0o111)):
            purpose, usage = get_script_info(file_path)
            if purpose:  # Only include scripts we can document
                scripts.append({
                    'name': file_path.name,
                    'purpose': purpose,
                    'usage': usage or f'./{file_path.name}' if file_path.suffix == '.sh' else f'python3 {file_path.name}'
                })
    
    # Generate markdown content
    lines = []
    lines.append("# Scripts Documentation")
    lines.append("")
    lines.append("This folder contains utility scripts for development, CI/CD, and maintenance tasks.")
    lines.append("")
    lines.append("## Available Scripts")
    lines.append("")
    lines.append("| Script | Purpose | Usage |")
    lines.append("|--------|---------|-------|")
    
    for script in scripts:
        lines.append(f"| [`{script['name']}`]({script['name']}) | {script['purpose']} | `{script['usage']}` |")
    
    lines.append("")
    lines.append("## Script Details")
    lines.append("")
    
    # Add detailed sections for each script
    for script in scripts:
        lines.append(f"### {script['name']}")
        lines.append("")
        lines.append(f"**Purpose**: {script['purpose']}")
        lines.append("")
        
        if script['usage']:
            lines.append(f"**Usage**: `{script['usage']}`")
            lines.append("")
    
    return '\n'.join(lines)

def main():
    scripts_dir = Path(__file__).parent
    readme_path = scripts_dir / "README.md"
    
    print("🔍 Scanning scripts directory...")
    
    # Generate new README content
    new_content = generate_readme(scripts_dir)
    
    # Check if content changed
    if readme_path.exists():
        old_content = readme_path.read_text()
        if old_content == new_content:
            print("✅ scripts/README.md is already up to date")
            return 0
    
    # Write new content
    readme_path.write_text(new_content)
    print(f"📝 Updated {readme_path}")
    
    # Validate with markdownlint
    print("🔍 Validating markdown...")
    try:
        result = subprocess.run(
            ['npx', 'markdownlint-cli2', str(readme_path)],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✅ Markdown lint: PASSED")
            return 0
        else:
            print("❌ Markdown lint: FAILED")
            print("Errors:")
            print(result.stdout)
            return 1
    except FileNotFoundError:
        print("⚠️  markdownlint-cli2 not found, skipping validation")
        return 0
    except subprocess.TimeoutExpired:
        print("❌ Markdown lint: TIMEOUT")
        return 1

if __name__ == "__main__":
    exit(main())
