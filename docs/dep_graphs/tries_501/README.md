# Fleet Manager ↔ Mule Dependency Analysis Summary

Generated: 2026-02-04

## Overview

This directory contains comprehensive interface dependency analysis showing how `fleet_manager` (parent repo) depends on `mule` (submodule).

## Files Generated

### 1. `fleet_manager_on_mule_deps.md` (31 lines)
**Quick Import Analysis**
- Files that import from mule: **4**
- Primary imports from fleet_manager's perspective
- **Usage**: Identify what fleet_manager needs from mule at a glance

Key findings:
- `fm_init.py` imports `load_mule_config`
- `utils/fleet_utils.py` imports `load_mule_config`
- `utils/route_preview_utils.py` imports `create_standalone_router`
- `utils/router_utils.py` imports `RoutePlannerInterface`

### 2. `fleet_manager_mule_detailed_analysis.md` (4,937 lines)
**Comprehensive Interface Analysis**
- Mule's exported functions & classes: **500+**
- Detailed function signatures with types
- Class definitions and methods
- **Usage**: Deep dive into interface contracts and implementation details

Includes:
- Full mule public API documentation
- Exported functions with parameter and return types
- Class hierarchies and method signatures
- Fleet Manager's usage patterns

### 3. `mule_dependency_analysis.md` (315 lines)
**Internal Mule Dependencies**
- Python files analyzed: **366** (from mule subdirectory)
- Internal module dependencies within mule
- External library usage counts
- **Usage**: Understanding mule's internal structure and external dependencies

### 4. `classes_mule.png` (114 bytes)
**Visual Class Diagram**
- Generated via `pyreverse` (pylint)
- Shows class relationships and hierarchies
- Note: Empty due to Python syntax errors in some mule files
- **Usage**: Visual reference for class structure (when syntax is clean)

## Tools Used

### 1. `scripts/analyze_mule_deps.py`
AST-based analyzer that:
- Parses Python code without executing
- Tracks imports and usage patterns
- Extracts function signatures and argument types
- Reports dependency chains

**Run:**
```bash
python3 ./scripts/analyze_mule_deps.py . mule docs/dep_graphs/fleet_manager_on_mule_deps.md
```

### 2. `scripts/analyze_detailed_mule_deps.py`
Enhanced analyzer providing:
- Complete mule public API extraction
- Function/class signature documentation
- Fleet Manager integration point analysis
- Type annotations when available

**Run:**
```bash
python3 ./scripts/analyze_detailed_mule_deps.py . mule docs/dep_graphs/fleet_manager_mule_detailed_analysis.md
```

### 3. `scripts/gen_mule_dep_graph.sh`
Bash script wrapping:
- `pyreverse` from pylint for visual graphs
- Graphviz `dot` for rendering
- Fallback to AST-based analysis on import errors

**Run:**
```bash
./scripts/gen_mule_dep_graph.sh
```

## Key Integration Points

### Core Interfaces

1. **`RoutePlannerInterface`** (`ati/control/bridge/router_planner_interface.py`)
   - Primary routing abstraction
   - Used in: `utils/router_utils.py`
   - Key methods: `create_router()`, `get_route_and_regimes()`

2. **`load_mule_config()`** (`ati/common/config.py`)
   - Configuration loader
   - Used in: `fm_init.py`, `utils/fleet_utils.py`
   - Parses mule configuration files

3. **`create_standalone_router()`** (dynamic routing)
   - Router factory
   - Used in: `utils/route_preview_utils.py`
   - Creates routing instances for path planning

## Architecture Insights

**Dependency Relationship:**
```
fleet_manager (parent)
    ↓ imports
mule (submodule)
    ├── ati.control          (control logic)
    ├── ati.perception       (sensor processing)
    ├── ati.slam            (localization)
    └── ati.common          (shared utilities)
```

**Fleet Manager Usage Pattern:**
- Primarily uses mule's control and routing interfaces
- Integrates with mule's configuration system
- Minimal cross-talk with perception/SLAM modules (decoupled)

## Recommendations

### For Interface Changes
1. **Check `fleet_manager_mule_detailed_analysis.md`** for current signatures
2. **Identify all call sites** using grep or this analysis
3. **Update fleet_manager** if argument counts/types change

### For Dependency Updates
1. Run analysis before making breaking changes
2. Use generated reports for change impact assessment
3. Re-generate after major refactors to document new state

### For New Developers
1. Start with `fleet_manager_on_mule_deps.md` for quick overview
2. Deep dive into `fleet_manager_mule_detailed_analysis.md` for details
3. Review source files for implementation context

## Technical Notes

- **AST Parsing**: Files with syntax errors are skipped gracefully
- **Type Annotations**: Extracted when present in code; "Any" used otherwise
- **External Libs**: Not tracked in this analysis (focus is intra-repo)
- **Generated Files**: Markdown text for version control; PNG diagrams for visual reference

