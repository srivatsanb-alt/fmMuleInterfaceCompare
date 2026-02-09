#!/usr/bin/env python3
"""Generate pyreverse diagrams from syntactically-valid mule files.

This script parses mule Python files with AST to skip files with syntax errors,
then invokes `pyreverse` on the remaining files to produce PNG diagrams.
"""
import ast
import subprocess
import shutil
import sys
from pathlib import Path


def find_valid_py_files(root: Path):
    files = []
    for p in sorted(root.rglob('*.py')):
        try:
            src = p.read_text(encoding='utf-8', errors='ignore')
            ast.parse(src, filename=str(p))
            files.append(str(p))
        except SyntaxError:
            # skip files that don't parse
            continue
        except Exception:
            continue
    return files


def main():
    repo_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
    mule_dir = repo_root / (sys.argv[2] if len(sys.argv) > 2 else 'mule')
    out_dir = repo_root / 'docs' / 'dep_graphs'
    out_format = (sys.argv[3] if len(sys.argv) > 3 else 'svg').lower()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not mule_dir.exists():
        print(f"Mule directory not found: {mule_dir}")
        sys.exit(1)

    valid_files = find_valid_py_files(mule_dir)
    print(f"Found {len(valid_files)} syntactically valid mule files")
    if not valid_files:
        print("No valid mule files to analyze with pyreverse.")
        sys.exit(2)

    pyreverse = shutil.which('pyreverse')
    if not pyreverse:
        print('pyreverse not found on PATH')
        sys.exit(3)

    cmd = [pyreverse, '-o', out_format, '-p', 'mule'] + valid_files
    print('Running:', ' '.join(cmd[:6]) + ' ...')
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print('pyreverse failed:', e)
        sys.exit(4)

    # move generated files to docs/dep_graphs and rename to classes_mule.png
    cwd = Path.cwd()
    generated = list(cwd.glob(f'classes_*.{out_format}')) + list(cwd.glob(f'packages_*.{out_format}'))
    for f in generated:
        target = out_dir / f.name
        try:
            f.replace(target)
            print(f"Saved: {target}")
        except Exception as e:
            print(f"Failed to move {f}: {e}")

    print('Done')


if __name__ == '__main__':
    main()
