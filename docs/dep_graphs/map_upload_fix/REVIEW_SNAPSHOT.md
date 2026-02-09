# Fleet Manager → Mule Dependencies Review Snapshot

**Generated for:** Pre-merge review
**Purpose:** Document fleet_manager dependencies on mule submodule APIs for maintainers

---

## Executive Summary

- **Files importing mule:** 3
- **Mule APIs used:** 8
- **Total API call sites:** 9

### Files Affected

| File | Mule Imports | Usage Count |
|------|-------------|-------------|
| `fm_init.py` | `load_mule_config` | 1 |
| `utils/fleet_utils.py` | `gbu`, `load_mule_config`, `mu`, `rpi` | 6 |
| `utils/router_utils.py` | `RoutePlannerInterface`, `grl` | 1 |

---

## API Usage Summary Table

| Mule API | Signature | Used By | Count | Lines |
|----------|-----------|---------|-------|-------|
| `load_mule_config` | `def load_mule_config(config_file)` | `fm_init.py`, `utils/fleet_utils.py` | 2 | fm_init.py:L37; utils/fleet_utils.py:L163 |
| `delete_station` | `def delete_station(name, stations)` | `utils/fleet_utils.py` | 2 | utils/fleet_utils.py:L411, L437 |
| `get_station` | `def get_station(pose)` | `utils/fleet_utils.py` | 1 | utils/fleet_utils.py:L395 |
| `maybe_update_gmaj` | `def maybe_update_gmaj(gmaj_path, wpsj_path, VERIFY_WPSJ_CHECKSUM)` | `utils/fleet_utils.py` | 1 | utils/fleet_utils.py:L146 |
| `process_dict` | `def process_dict(terminal_lines)` | `utils/fleet_utils.py` | 1 | utils/fleet_utils.py:L175 |
| `process_stations_info` | `def process_stations_info(stations)` | `utils/fleet_utils.py` | 1 | utils/fleet_utils.py:L176 |
| `get_dense_path` | `def get_dense_path(final_route)` | `utils/router_utils.py` | 1 | utils/router_utils.py:L14 |
| `get_checksum` | `def get_checksum(fname, fn=hashlib.sha1)` | `utils/fleet_utils.py` | 1 | utils/fleet_utils.py:L177 |

---

## Detailed Dependencies by File

### `fm_init.py`

**Imports from mule:** `load_mule_config`

| Function | Mule API | Args | Line |
|----------|----------|------|------|
| `regenerate_mule_config()` | `load_mule_config` | `os.getenv(...)` | 37 |

**Impact:** Configuration loading — changes to mule config format affect initialization.

---

### `utils/fleet_utils.py`

**Imports from mule:** `gbu`, `load_mule_config`, `mu`, `rpi`

| Function | Mule API | Args | Line |
|----------|----------|------|------|
| `maybe_create_gmaj_file()` | `maybe_update_gmaj` | `gmaj_path, wpsj_path, True` | 146 |
| `maybe_create_graph_object()` | `get_checksum` | `gmaj_path` | 177 |
| `maybe_create_graph_object()` | `load_mule_config` | `` | 163 |
| `maybe_create_graph_object()` | `process_dict` | `terminal_lines` | 175 |
| `maybe_create_graph_object()` | `process_stations_info` | `stations` | 176 |
| `FleetUtils.delete_station()` | `get_station` | `station_name` | 395 |
| `FleetUtils.delete_invalid_stations()` | `delete_station` | `dbsession, st.name` | 411 |
| `FleetUtils.delete_fleet()` | `delete_station` | `dbsession, station.name` | 437 |

**Impact:** Core fleet management — station and graph-related APIs are critical.

---

### `utils/router_utils.py`

**Imports from mule:** `RoutePlannerInterface`, `grl`

| Function | Mule API | Args | Line |
|----------|----------|------|------|
| `get_dense_path()` | `get_dense_path` | `final_route` | 14 |

**Impact:** Route planning and path generation — ensure signature stability.

---

## Breaking Change Checklist

Before merging or tagging, verify:

- [ ] No mule API signatures changed (arg counts/defaults)
- [ ] Imported symbols exist and module paths are stable
- [ ] Behavior changes in mule APIs are validated against fleet_manager usages

## Visuals

- `docs/dep_graphs/classes_fleet_manager_on_mule.svg`
- `docs/dep_graphs/packages_fleet_manager_on_mule.svg`
- `docs/dep_graphs/classes_mule.svg`
- `docs/dep_graphs/packages_mule.svg`

---

Generated from `docs/dep_graphs/fleet_manager_mule_detailed_analysis.md`.
