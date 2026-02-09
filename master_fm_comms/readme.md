The following processes outline the data flow from FM to Sanjaya, including the conditions under which updates occur:

## Initial Updates (Upon Restart or Configuration Change related to fleet)

1. update_fm_version_info

2. update_fleet_info

3. upload_map_files

4. update_sherpa_info

- These updates will only occur when FM is restarted or when specific configurations are modified.

## update_trip_info

- Occurs after every update frequency specified in the config editor.

## update_trip_analytics

- Occurs after every update frequency specified in the config editor.

## update_sherpa_oee

- Occurs every 30 minutes.

## update_fm_incidents

- Occurs after every update frequency specified in the config editor.

## upload_important_files

- Occurs after every update frequency specified in the config editor.
