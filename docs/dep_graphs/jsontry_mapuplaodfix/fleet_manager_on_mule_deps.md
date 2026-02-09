# Fleet Manager → Mule Submodule Dependencies

This report shows interface dependencies: which files in fleet_manager depend on mule.

**Total files in fleet_manager that import mule:** 3
**Total files analyzed (excluding mule):** 226

## Dependency Graph

### root/

**1 files import from mule:**

- **fm_init.py**
  - imports: `mule`
    - from: `load_mule_config`

### utils/

**2 files import from mule:**

- **utils/fleet_utils.py**
  - imports: `mule`
    - from: `load_mule_config`
- **utils/router_utils.py**
  - imports: `mule`
    - from: `RoutePlannerInterface`

