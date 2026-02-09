#!/usr/bin/env python3
"""
Analyze how the parent fleet_manager repository depends on the mule submodule.
Generates an interface dependency graph showing what imports mule from where.
"""
import os
import sys
import ast
from pathlib import Path
from collections import defaultdict

def analyze_imports(py_file):
    """Extract import statements from a Python file."""
    imports = set()
    from_imports = defaultdict(set)  # module -> set of specific imports
    try:
        with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
            tree = ast.parse(f.read(), filename=py_file)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split('.')[0]
                    imports.add(root)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root = node.module.split('.')[0]
                    imports.add(root)
                    # Track what's specifically imported
                    for alias in node.names:
                        from_imports[root].add(alias.name)
    except SyntaxError:
        pass  # Skip files with syntax errors
    return imports, from_imports

def generate_fleet_manager_on_mule_deps(repo_root, mule_submodule, output_file):
    """
    Generate a report showing fleet_manager -> mule dependencies.
    Analyzes all Python files outside of mule for imports from mule.
    """
    repo_path = Path(repo_root)
    mule_path = repo_path / mule_submodule
    
    # Find all Python files in repo (excluding mule and common excludes)
    exclude_dirs = {mule_submodule, '__pycache__', '.git', 'node_modules', '.venv', 'venv', 'build', 'dist'}
    py_files = [
        f for f in repo_path.glob('**/*.py') 
        if not any(part in exclude_dirs for part in f.relative_to(repo_path).parts)
    ]
    
    print(f"Found {len(py_files)} Python files in fleet_manager (excluding mule)")
    
    # Track files that import from mule and what they import
    mule_importers = defaultdict(lambda: {'files': set(), 'imports': set()})
    mule_imports_by_file = defaultdict(lambda: {'modules': set(), 'specifics': set()})
    
    for py_file in py_files:
        imports, from_imports = analyze_imports(py_file)
        
        if 'mule' in imports or any('mule' in imp for imp in imports):
            rel_path = str(py_file.relative_to(repo_path))
            
            # Track this file as a mule importer
            for module in imports:
                if 'mule' in module or module == 'mule':
                    mule_imports_by_file[rel_path]['modules'].add(module)
                    if module in from_imports:
                        mule_imports_by_file[rel_path]['specifics'].update(from_imports[module])
    
    # Group by top-level directories
    importers_by_dir = defaultdict(list)
    for file_path in mule_imports_by_file:
        parts = Path(file_path).parts
        if len(parts) > 1:
            top_dir = parts[0]
        else:
            top_dir = 'root'
        importers_by_dir[top_dir].append(file_path)
    
    # Write report
    with open(output_file, 'w') as f:
        f.write("# Fleet Manager → Mule Submodule Dependencies\n\n")
        f.write("This report shows interface dependencies: which files in fleet_manager depend on mule.\n\n")
        f.write(f"**Total files in fleet_manager that import mule:** {len(mule_imports_by_file)}\n")
        f.write(f"**Total files analyzed (excluding mule):** {len(py_files)}\n\n")
        
        f.write("## Dependency Graph\n\n")
        
        if not mule_imports_by_file:
            f.write("No dependencies found from fleet_manager on mule.\n")
        else:
            for directory in sorted(importers_by_dir.keys()):
                files = importers_by_dir[directory]
                f.write(f"### {directory}/\n\n")
                f.write(f"**{len(files)} files import from mule:**\n\n")
                
                for file_path in sorted(files):
                    modules = mule_imports_by_file[file_path]['modules']
                    specifics = mule_imports_by_file[file_path]['specifics']
                    
                    f.write(f"- **{file_path}**\n")
                    for mod in sorted(modules):
                        f.write(f"  - imports: `{mod}`\n")
                        if specifics:
                            # Show first few specific imports
                            spec_list = sorted(specifics)[:5]
                            f.write(f"    - from: {', '.join(f'`{s}`' for s in spec_list)}")
                            if len(spec_list) < len(specifics):
                                f.write(f" (+{len(specifics) - len(spec_list)} more)")
                            f.write("\n")
                
                f.write("\n")
    
    print(f"✓ Fleet Manager → Mule dependency report saved to: {output_file}")
    print(f"  Files that import mule: {len(mule_imports_by_file)}")

if __name__ == '__main__':
    repo_root = sys.argv[1] if len(sys.argv) > 1 else '.'
    mule_submodule = sys.argv[2] if len(sys.argv) > 2 else 'mule'
    output_file = sys.argv[3] if len(sys.argv) > 3 else 'docs/dep_graphs/fleet_manager_on_mule_deps.md'
    
    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    generate_fleet_manager_on_mule_deps(repo_root, mule_submodule, output_file)
