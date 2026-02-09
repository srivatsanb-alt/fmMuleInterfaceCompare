# Fleet Manager → Mule Dependencies Review Snapshot

**Generated for:** Pre-merge and tag creation review  
**Last updated:** 2026-02-06  
**Purpose:** Document all fleet_manager dependencies on mule submodule APIs

---

## Executive Summary

- **Files importing mule:** 4
- **Mule APIs used:** 7
- **Total API call sites:** 8

### Files Affected

| File | Mule Imports | Usage Count |
|------|-------------|-------------|
| `fm_init.py` | `load_mule_config` | 1 |
| `utils/fleet_utils.py` | `gbu`, `load_mule_config`, `rpi` | 5 |
| `utils/route_preview_utils.py` | `create_standalone_router` | 0 |
| `utils/router_utils.py` | `RoutePlannerInterface`, `grl` | 1 |

---

## API Usage Summary Table

| Mule API | Signature | Used By | Count | Lines |
|----------|-----------|---------|-------|-------|
| `load_mule_config` | `def load_mule_config(config_file)` | `fm_init.py`, `utils/fleet_utils.py` | 1 | L37 |
| `delete_station` | `def delete_station(name, stations)` | `utils/fleet_utils.py` | 2 | L404, L430 |
| `get_station` | `def get_station(pose)` | `utils/fleet_utils.py` | 1 | L388 |
| `maybe_update_gmaj` | `def maybe_update_gmaj(gmaj_path, wpsj_path, VERIFY_WPSJ_CHECKSUM)` | `utils/fleet_utils.py` | 1 | L154 |
| `process_dict` | `def process_dict(terminal_lines)` | `utils/fleet_utils.py` | 1 | L177 |
| `process_stations_info` | `def process_stations_info(stations)` | `utils/fleet_utils.py` | 1 | L178 |
| `get_dense_path` | `def get_dense_path(final_route)` | `utils/router_utils.py` | 1 | L14 |

---

## Detailed Dependencies by File

### `fm_init.py`

**Imports from mule:** `load_mule_config`

| Function | Mule API | Args | Line |
|----------|----------|------|------|
| `regenerate_mule_config()` | `load_mule_config` | `os.getenv(...)` | 37 |

**Impact:** Configuration loading. Changes to mule config format will affect initialization.

---

### `utils/fleet_utils.py`

**Imports from mule:** `gbu`, `load_mule_config`, `rpi`

| Function | Mule API | Args | Line |
|----------|----------|------|------|
| `maybe_create_gmaj_file()` | `maybe_update_gmaj` | `gmaj_path, wpsj_path, True` | 154 |
| `maybe_create_graph_object()` | `process_dict` | `terminal_lines` | 177 |
| `maybe_create_graph_object()` | `process_stations_info` | `stations` | 178 |
| `FleetUtils.delete_station()` | `get_station` | `station_name` | 388 |
| `FleetUtils.delete_invalid_stations()` | `delete_station` | `dbsession, st.name` | 404 |
| `FleetUtils.delete_fleet()` | `delete_station` | `dbsession, station.name` | 430 |

**Impact:** Core fleet management operations. Heavy dependency on station/graph management APIs.

---

### `utils/route_preview_utils.py`

**Imports from mule:** `create_standalone_router`

**Status:** Imported but no active function calls tracked.

---

### `utils/router_utils.py`

**Imports from mule:** `RoutePlannerInterface`, `grl`

| Function | Mule API | Args | Line |
|----------|----------|------|------|
| `get_dense_path()` | `get_dense_path` | `final_route` | 14 |

**Impact:** Route planning and path generation. Argument count must match: 1 arg required.

---

## Breaking Change Checklist

Before merging or creating a tag, verify:

- [ ] **Signature changes:** No mule API signatures changed in arguments or return types
- [ ] **Imports:** All imported mule symbols still exist and are exported
- [ ] **File locations:** All mule module paths remain valid (no refactoring)
- [ ] **Behavior changes:** No breaking logic changes in called mule APIs

### Critical APIs to Monitor

High-risk APIs (used frequently):
- `delete_station(name, stations)` — used 2x in fleet deletion/cleanup
- `process_dict(terminal_lines)` — used in graph creation
- `process_stations_info(stations)` — used in graph creation

---

## Related Documentation

- **Full Details:** [fleet_manager_mule_detailed_analysis.md](fleet_manager_mule_detailed_analysis.md)
- **Visual Diagrams:**
  - `classes_fleet_manager_on_mule.svg` — Fleet manager class structure
  - `packages_fleet_manager_on_mule.svg` — Fleet manager package dependencies
  - `classes_mule.svg` — Full mule architecture
  - `packages_mule.svg` — Full mule packages
