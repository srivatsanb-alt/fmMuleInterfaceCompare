#!/usr/bin/env python3
"""
Detailed analysis of fleet_manager → mule dependencies.
Extracts function signatures, classes, and tracks cross-module calls with arguments.
Generates comprehensive interface documentation in JSON format.
"""
import os
import sys
import ast
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Set, Optional
from datetime import datetime

class CodeAnalyzer(ast.NodeVisitor):
    """Extract function/class definitions and calls from Python AST."""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.module_name = Path(filepath).stem
        self.functions = {}  # func_name -> {args, return_type, lineno}
        self.classes = {}    # class_name -> {bases, methods, lineno}
        self.calls = []      # [(caller, callee, args_as_str, lineno)]
        self.imports = defaultdict(set)  # module -> set of names
        self.import_aliases = {}  # alias -> original_module (e.g., 'mu' -> 'mule.ati.tools.map_utils')
        self.var_origins = {}  # var_name or attr -> origin (e.g. 'mule.RoutePlannerInterface.router')
        self.current_function = None
        self.current_class = None
        
    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports[alias.name].add(alias.asname or alias.name)
            # Track alias -> original module mapping for call resolution
            if alias.asname:
                self.import_aliases[alias.asname] = alias.name
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            for alias in node.names:
                self.imports[node.module].add(alias.name)
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        args_str = self._extract_args(node.args)
        return_type = self._extract_return_type(node)
        
        func_info = {
            'name': node.name,
            'args': args_str,
            'return_type': return_type,
            'lineno': node.lineno,
            'decorators': [d.id if isinstance(d, ast.Name) else str(d) for d in node.decorator_list],
            'calls': []
        }
        # Store required and total arg counts for matching calls
        required_args, total_args = self._get_arg_counts(node.args)
        func_info['required_args'] = required_args
        func_info['total_args'] = total_args
        
        if self.current_class:
            if self.current_class not in self.classes:
                self.classes[self.current_class] = {'methods': {}}
            self.classes[self.current_class]['methods'][node.name] = func_info
        else:
            self.functions[node.name] = func_info
        
        # Visit function body to find calls
        prev_func = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = prev_func
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        # Treat async functions same as regular functions
        node.__class__ = ast.FunctionDef
        self.visit_FunctionDef(node)
    
    def visit_ClassDef(self, node: ast.ClassDef):
        bases_str = ', '.join(self._get_name(base) for base in node.bases)
        class_info = {
            'name': node.name,
            'bases': bases_str,
            'lineno': node.lineno,
            'methods': {}
        }
        self.classes[node.name] = class_info
        
        prev_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = prev_class
    
    def visit_Call(self, node: ast.Call):
        if self.current_function or self.current_class:
            caller = f"{self.current_class}.{self.current_function}" if self.current_class else self.current_function
            callee = self._get_call_name(node.func)
            args_str = self._extract_call_args(node.args)
            
            self.calls.append({
                'caller': caller,
                'callee': callee,
                'args': args_str,
                'lineno': node.lineno
            })
        
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        """Capture assignments that originate from calls into mule factories.
        Examples handled:
          self.router = RoutePlannerInterface(...).router
          router = RoutePlannerInterface(...).router
          v = SomeFactory(...)
        """
        # only consider simple single-target assignments for now
        try:
            value = node.value
            origin = None
            # Case: Attribute(Call(...), attr)
            if isinstance(value, ast.Attribute) and isinstance(value.value, ast.Call):
                call = value.value
                call_name = self._get_call_name(call.func)
                origin = f"{call_name}.{value.attr}"
            # Case: direct Call(...) assigned
            elif isinstance(value, ast.Call):
                call = value
                call_name = self._get_call_name(call.func)
                origin = call_name

            if origin:
                for target in node.targets:
                    if isinstance(target, ast.Attribute):
                        tname = self._get_name(target)
                        self.var_origins[tname] = origin
                    elif isinstance(target, ast.Name):
                        self.var_origins[target.id] = origin
        except Exception:
            pass
        self.generic_visit(node)
    
    def _extract_args(self, args: ast.arguments) -> str:
        """Extract function arguments as readable string."""
        params = []
        for arg in args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {self._get_annotation(arg.annotation)}"
            params.append(arg_str)
        return ', '.join(params)

    def _get_arg_counts(self, args: ast.arguments) -> Tuple[int, int]:
        """Return (required_args, total_args) for a function.
        Required = args without defaults, Total = all args.
        """
        total = len(args.args)
        defaults = len(getattr(args, 'defaults', []))
        required = total - defaults
        return (required, total)
    
    
    def _extract_return_type(self, node: ast.FunctionDef) -> Optional[str]:
        """Extract return type annotation."""
        if node.returns:
            return self._get_annotation(node.returns)
        return None
    
    def _extract_call_args(self, args: List) -> str:
        """Extract call arguments as readable string."""
        arg_strs = []
        for arg in args:
            if isinstance(arg, ast.Constant):
                arg_strs.append(repr(arg.value)[:30])
            elif isinstance(arg, ast.Name):
                arg_strs.append(arg.id)
            elif isinstance(arg, ast.Attribute):
                arg_strs.append(self._get_name(arg))
            elif isinstance(arg, ast.Call):
                arg_strs.append(f"{self._get_call_name(arg.func)}(...)")
            else:
                arg_strs.append("...")
        return ', '.join(arg_strs[:3]) + ("..." if len(arg_strs) > 3 else "")
    
    def _get_annotation(self, node) -> str:
        """Convert annotation AST to string."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self._get_name(node)
        elif isinstance(node, ast.Subscript):
            return f"{self._get_annotation(node.value)}[...]"
        return "Any"
    
    def _get_call_name(self, node) -> str:
        """Extract function name from call."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self._get_name(node)
        return "unknown"
    
    def _get_name(self, node) -> str:
        """Extract name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return str(node)


def analyze_codebase(root_path: str, exclude_dirs: Set[str]) -> Dict:
    """Analyze entire codebase for functions, classes, and calls."""
    root = Path(root_path)
    results = defaultdict(lambda: {'functions': {}, 'classes': {}, 'calls': [], 'imports': defaultdict(set)})
    
    py_files = [
        f for f in root.glob('**/*.py')
        if not any(part in exclude_dirs for part in f.relative_to(root).parts)
    ]
    
    print(f"Analyzing {len(py_files)} Python files...")
    
    for py_file in py_files:
        try:
            with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                tree = ast.parse(f.read(), filename=str(py_file))
            
            analyzer = CodeAnalyzer(str(py_file))
            analyzer.visit(tree)
            
            rel_path = str(py_file.relative_to(root))
            results[rel_path]['functions'] = analyzer.functions
            results[rel_path]['classes'] = analyzer.classes
            results[rel_path]['calls'] = analyzer.calls
            results[rel_path]['imports'] = dict(analyzer.imports)
            results[rel_path]['import_aliases'] = dict(analyzer.import_aliases)
            results[rel_path]['var_origins'] = dict(analyzer.var_origins)
        except Exception as e:
            print(f"  ⚠ Error analyzing {py_file}: {e}")
    
    return results


def generate_detailed_report(repo_root: str, mule_submodule: str, output_file: str):
    """Generate comprehensive interface dependency report in JSON format."""
    repo_path = Path(repo_root)
    mule_path = repo_path / mule_submodule
    
    exclude_dirs = {mule_submodule, '__pycache__', '.git', 'node_modules', '.venv', 'venv'}
    
    # Analyze fleet_manager code
    print("\n=== Analyzing fleet_manager ===")
    fm_code = analyze_codebase(repo_root, exclude_dirs)
    
    # Analyze mule code to understand exposed interfaces
    print("\n=== Analyzing mule submodule ===")
    mule_code = analyze_codebase(str(mule_path), {'__pycache__', '.git'})
    
    # Extract mule's public interfaces
    mule_public = extract_mule_public_api(mule_code)
    
    # Find all places where fleet_manager calls mule
    mule_usage = find_mule_usage(fm_code, mule_public)
    
    # Build JSON report structure
    report = {
        "metadata": {
            "version": "1.0",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "repo_root": str(repo_path),
            "mule_submodule": mule_submodule,
            "mule_path": str(mule_path)
        },
        "mule_public_api": {
            "functions": {},
            "classes": {}
        },
        "fleet_manager_usage": {
            "importing_files": {},
            "interface_calls": {},
            "call_chains": []
        },
        "statistics": {
            "mule_functions_count": 0,
            "mule_classes_count": 0,
            "mule_methods_count": 0,
            "fleet_manager_files_count": len(fm_code),
            "fleet_manager_importing_mule_count": 0,
            "interface_usage_count": 0,
            "total_call_chains": 0
        }
    }
    
    # Populate mule public API
    for file_path, funcs in sorted(mule_public['functions'].items()):
        report["mule_public_api"]["functions"][file_path] = {}
        for fname, finfo in funcs.items():
            report["mule_public_api"]["functions"][file_path][fname] = {
                "signature": f"def {fname}({finfo['args']})",
                "args": finfo['args'],
                "return_type": finfo.get('return_type', ''),
                "line": finfo.get('lineno'),
                "decorators": finfo.get('decorators', []),
                "required_args": finfo.get('required_args', 0),
                "total_args": finfo.get('total_args', 0)
            }
            report["statistics"]["mule_functions_count"] += 1
    
    for file_path, classes in sorted(mule_public['classes'].items()):
        report["mule_public_api"]["classes"][file_path] = {}
        for cname, cinfo in classes.items():
            methods = {}
            for mname, minfo in cinfo.get('methods', {}).items():
                if not mname.startswith('_'):
                    methods[mname] = {
                        "signature": f"{mname}({minfo['args']})",
                        "args": minfo['args'],
                        "return_type": minfo.get('return_type', ''),
                        "line": minfo.get('lineno'),
                        "required_args": minfo.get('required_args', 0),
                        "total_args": minfo.get('total_args', 0)
                    }
                    report["statistics"]["mule_methods_count"] += 1
            
            report["mule_public_api"]["classes"][file_path][cname] = {
                "bases": cinfo.get('bases', ''),
                "line": cinfo.get('lineno'),
                "methods": methods
            }
            report["statistics"]["mule_classes_count"] += 1
    
    # Populate fleet_manager usage
    report["statistics"]["fleet_manager_importing_mule_count"] = len(mule_usage['direct_imports'])
    
    for file_path in sorted(mule_usage['direct_imports']):
        imports = mule_usage['direct_imports'][file_path]
        report["fleet_manager_usage"]["importing_files"][file_path] = {
            "imports": sorted(list(imports))
        }
    
    for interface, usage_list in sorted(mule_usage['interface_usage'].items()):
        report["fleet_manager_usage"]["interface_calls"][interface] = {
            "mule_definition": mule_public['interface_sigs'].get(interface, 'Not found'),
            "usage_count": len(usage_list),
            "usage_locations": []
        }
        for usage in usage_list:
            report["fleet_manager_usage"]["interface_calls"][interface]["usage_locations"].append({
                "file": usage['file'],
                "line": usage['line'],
                "caller": usage['caller'],
                "call_args": usage['args'],
                "arg_count": usage.get('arg_count', 0),
                "return_used": usage.get('return_used', False),
                "resolved_from": usage.get('resolved_from')
            })
        report["statistics"]["interface_usage_count"] += 1
    
    report["fleet_manager_usage"]["call_chains"] = sorted(mule_usage['call_chains'])
    report["statistics"]["total_call_chains"] = len(mule_usage['call_chains'])
    
    # Write JSON report
    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"✓ Detailed report saved to: {output_file}")


def extract_mule_public_api(mule_code: Dict) -> Dict:
    """Extract Mule's public functions and classes."""
    public = {
        'functions': {},
        'classes': {},
        'interface_sigs': {}
    }
    
    for file_path, code_info in mule_code.items():
        if code_info['functions']:
            public['functions'][file_path] = code_info['functions']
            for fname, finfo in code_info['functions'].items():
                if not fname.startswith('_'):
                    sig = f"def {fname}({finfo['args']})"
                    if finfo['return_type']:
                        sig += f" → {finfo['return_type']}"
                    public['interface_sigs'][fname] = sig
        
        if code_info['classes']:
            public['classes'][file_path] = code_info['classes']
            for cname, cinfo in code_info['classes'].items():
                if not cname.startswith('_'):
                    for mname, minfo in cinfo.get('methods', {}).items():
                        if not mname.startswith('_'):
                            sig = f"{cname}.{mname}({minfo['args']})"
                            if minfo['return_type']:
                                sig += f" → {minfo['return_type']}"
                            public['interface_sigs'][mname] = sig
    
    return public


def find_mule_usage(fm_code: Dict, mule_public: Dict) -> Dict:
    """Find where fleet_manager uses mule APIs.
    Matches full function names + argument counts (not substrings).
    Resolves import aliases (e.g., mu.get_checksum -> mule.ati.tools.map_utils.get_checksum).
    """
    usage = {
        'direct_imports': {},
        'call_chains': [],
        'interface_usage': defaultdict(list)
    }
    
    # Build map of func_name -> list of (required_args, total_args, signature)
    funcs_by_name = {}
    for file_path, funcs in mule_public.get('functions', {}).items():
        for func_name, func_info in funcs.items():
            required = func_info.get('required_args') if func_info.get('required_args') is not None else None
            total = func_info.get('total_args') if func_info.get('total_args') is not None else None
            # fallback: compute from args string
            if required is None or total is None:
                args = func_info.get('args', '')
                parts = [p.strip() for p in args.split(',') if p.strip()]
                total = len(parts)
                # assume all are required if we don't know defaults
                required = total
            funcs_by_name.setdefault(func_name, []).append((required, total, func_name))
    
    for file_path, code_info in fm_code.items():
        mule_imports = set()
        for mod_key, names in code_info.get('imports', {}).items():
            root = mod_key.split('.')[0]
            if root in ('mule', 'ati'):
                mule_imports.update(names if isinstance(names, (set, list)) else {names})
        if mule_imports:
            usage['direct_imports'][file_path] = mule_imports
            
            # Get import aliases for this file (e.g., 'mu' -> 'mule.ati.tools.map_utils')
            import_aliases = code_info.get('import_aliases', {})
            
            # Find calls to mule functions
            for call in code_info['calls']:
                callee = call['callee']
                args_str = call['args']
                
                # Resolve alias if callee starts with an alias
                # e.g., 'mu.get_checksum' -> check if 'mu' is an alias
                resolved_callee = callee
                if '.' in callee:
                    prefix = callee.split('.')[0]
                    if prefix in import_aliases:
                        # Replace alias with actual module
                        resolved_module = import_aliases[prefix]
                        resolved_callee = resolved_module + '.' + '.'.join(callee.split('.')[1:])
                
                # Extract function name (last part after .)
                func_name = resolved_callee.split('.')[-1] if '.' in resolved_callee else resolved_callee
                
                # Count call arguments
                call_arg_count = len([p.strip() for p in args_str.split(',') if p.strip()]) if args_str else 0
                
                # Try matching by name and arg count range (respecting defaults)
                candidates = funcs_by_name.get(func_name, [])
                matched = False
                for required, total, interface in candidates:
                    if required <= call_arg_count <= total:
                        usage['interface_usage'][interface].append({
                            'file': file_path,
                            'caller': call['caller'],
                            'args': call['args'],
                            'line': call['lineno'],
                            'return_used': True,
                            'arg_count': call_arg_count
                        })
                        usage['call_chains'].append(
                            f"{file_path}:{call['caller']}() → {interface}({call['args']})"
                        )
                        matched = True
                        break
                if matched:
                    continue

                # If callee is a member call like 'self.router.generate_path_wps_for_viz',
                # try to resolve 'self.router' origin from var_origins
                if '.' in callee:
                    prefix, method = callee.rsplit('.', 1)
                    var_origins = code_info.get('var_origins', {})
                    origin = var_origins.get(prefix)
                    if origin:
                        # origin could be like 'RoutePlannerInterface.router' or 'mule.RoutePlannerInterface.router'
                        # match method name + arg count to mule interface (respecting defaults)
                        candidates = funcs_by_name.get(method, [])
                        for required, total, interface in candidates:
                            if required <= call_arg_count <= total:
                                usage['interface_usage'][interface].append({
                                    'file': file_path,
                                    'caller': call['caller'],
                                    'args': call['args'],
                                    'line': call['lineno'],
                                    'return_used': True,
                                    'arg_count': call_arg_count,
                                    'resolved_from': origin,
                                })
                                usage['call_chains'].append(
                                    f"{file_path}:{call['caller']}() → {origin}.{interface}({call['args']})"
                                )
                                break
    
    return usage


def _get_interface_argcount(mule_public: Dict, interface_name: str) -> int:
    """Return number of arguments for an interface (function or method).
    For methods, subtract 'self' if present.
    """
    # Search functions
    for file_path, funcs in mule_public.get('functions', {}).items():
        if interface_name in funcs:
            args = funcs[interface_name].get('args', '')
            if not args:
                return 0
            parts = [p.strip() for p in args.split(',') if p.strip()]
            return len(parts)

    # Search methods in classes
    for file_path, classes in mule_public.get('classes', {}).items():
        for cname, cinfo in classes.items():
            for mname, minfo in cinfo.get('methods', {}).items():
                if mname == interface_name:
                    args = minfo.get('args', '')
                    parts = [p.strip() for p in args.split(',') if p.strip()]
                    # subtract 'self' if present
                    if parts and parts[0] == 'self':
                        return max(0, len(parts) - 1)
                    return len(parts)

    return 0


if __name__ == '__main__':
    repo_root = sys.argv[1] if len(sys.argv) > 1 else '.'
    mule_submodule = sys.argv[2] if len(sys.argv) > 2 else 'mule'
    output_file = sys.argv[3] if len(sys.argv) > 3 else 'docs/dep_graphs/fleet_manager_mule_detailed_analysis.json'
    
    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    generate_detailed_report(repo_root, mule_submodule, output_file)
