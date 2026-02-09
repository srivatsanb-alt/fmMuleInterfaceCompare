from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
import os
import json
import logging
import app.routers.dependencies as dpd
from utils.auth_utils import AuthValidator

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/staging_area",
    tags=["staging_area"],
)

@router.post("/get_staging_area")
async def get_staging_area(
    fleet_names: List[str], user_name=Depends(AuthValidator('fm'))
) -> Dict[str, Any]:
    """
    Get staging_areas.json content and station names for fleets that contain staging_areas.json.
    Args:
        fleet_names: List of fleet names to check for staging areas
    Returns:
        Dictionary containing staging_areas.json content and station names for fleets
        that have staging_areas.json in their map folder. Station names are extracted
        from grid_map_attributes.json where station_type is "station".
    """
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    result = {}
    static_base_path = os.getenv("FM_STATIC_DIR", "static")

    for fleet_name in fleet_names:
        try:
            fleet_path = os.path.join(static_base_path, fleet_name)
            map_path = os.path.join(fleet_path, "map")
            staging_areas_file = os.path.join(map_path, "staging_areas.json")
            grid_map_file = os.path.join(map_path, "grid_map_attributes.json")

            # Check if staging_areas.json exists
            if os.path.exists(staging_areas_file):
                try:
                    # Read staging areas data
                    with open(staging_areas_file, "r") as f:
                        staging_areas_data = json.load(f)

                    # Read grid map attributes to get station names
                    station_names = []
                    if os.path.exists(grid_map_file):
                        try:
                            with open(grid_map_file, "r") as f:
                                grid_map_data = json.load(f)

                            # Extract station names where station ID is 3 digits or less
                            stations_info = grid_map_data.get("stations_info", {})

                            for station_id, station_data in stations_info.items():
                                # Check if station ID is 3 digits or less (numeric check)
                                try:
                                    station_id_num = int(station_id)
                                    if station_id_num <= 999:  # 3 digits or less
                                        station_name = station_data.get("station_name")
                                        if station_name:
                                            station_names.append(station_name)
                                except (ValueError, TypeError):
                                    # Skip non-numeric station IDs
                                    continue

                            logger.info(
                                f"Fleet '{fleet_name}': Found {len(station_names)} stations with ID ≤ 999"
                            )

                        except json.JSONDecodeError as e:
                            logger.error(
                                f"Invalid JSON in grid_map_attributes.json for fleet '{fleet_name}': {str(e)}"
                            )
                        except Exception as e:
                            logger.error(
                                f"Error reading grid_map_attributes.json for fleet '{fleet_name}': {str(e)}"
                            )
                    else:
                        logger.debug(
                            f"Fleet '{fleet_name}' does not have grid_map_attributes.json"
                        )

                    # Include staging_areas.json data and station names in the result
                    result[fleet_name] = {
                        **staging_areas_data,
                        "station_names": station_names
                    }

                except json.JSONDecodeError as e:
                    logger.error(
                        f"Invalid JSON in staging_areas.json for fleet '{fleet_name}': {str(e)}"
                    )
                    # Skip fleets with invalid JSON
                    continue
                except Exception as e:
                    logger.error(
                        f"Error reading staging_areas.json for fleet '{fleet_name}': {str(e)}"
                    )
                    # Skip fleets with read errors
                    continue
            else:
                # Skip fleets without staging_areas.json (don't include in result)
                logger.debug(
                    f"Fleet '{fleet_name}' does not have staging_areas.json - skipping"
                )
                continue

        except Exception as e:
            logger.error(f"Unexpected error processing fleet '{fleet_name}': {str(e)}")
            # Skip fleets with unexpected errors
            continue

    return result