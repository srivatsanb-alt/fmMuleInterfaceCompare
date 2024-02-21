## Introduction ##

This directory contains periodic scripts called at [`main.py`](../main.py) as process, we have added decorator into most of them.  There are two types of decorators used:

1. [`report_error`](/utils/util.py#report_error) : This decorator runs the script within a try and except block and if an error occurs, it will log the error in a JSON format to the log file in `static/fm_errors` ([`proc_exeption`](/utils/util.py#proc_exeption)).

2. [`proc_retry`](/utils/util.py#proc_error) : This decorator triggers when an error occurs and retries the script until it no longer encounters any errors.

## periodic_backup ##

The [periodic_backup](./periodic_backup.py) scripts manages the backup process for logs and plugin data. It also handles the pruning of old backup data to ensure efficient storage management, either every 30 minutes or when the `data_backup_size` exceeds `keep_size_mb`.

It creates a folder named `static/data_backup` as `fm_backup_path`, and a subfolder named `{start_time}_data` within `fm_backup_path` as current_data. This is where logs and all plugin databases in CSV format are stored.

The `FM_IMAGE_INFO` log is stored at `fm_backup_path/current_data/info.txt`.

The function retrieves all the plugin databases. For each database, it creates a directory named `{database_name}_db` within `fm_backup_path/current_data`. The data for each table in the database is then stored in a CSV file named model.csv within the corresponding database directory `fm_backup_path/current_data/{database_name}_db/model.csv`.

## conditional_trips ##

The [book_conditional_trips](./conditional_trips.py#@report_error) script is used to book conditional trips such as `auto_park` and `battery_swap`. This script retrieves the `conditional_trips_config` from mongo_client and extracts `trip_types` from the JSON. It then calls the corresponding function for each trip type listed in `trip_types`.

When booking auto_park trips, the function first obtains the `idling_sherpa_status`, which is determined by whether the current time minus the end time of the last trip is greater than a certain threshold. For idling sherpas, the script checks if the sherpa is not already parked before initiating the parking process.

For booking battery_swap trips, the script first identifies `low_battery_sherpa_status`, which is based on sherpas with battery_status below a threshold. The script then checks for a saved route and whether the sherpa is already booked. If the sherpa is not booked, the script verifies the number of trips already booked for the battery_swap station. If this number is less than the `max_trips`, then battery_swap conditional trip is booked.

## periodic_fm_health_check ##

The [`periodic_fm_health_check`](./periodic_fm_health_check.py) script is a periodic task that performs several checks and records system performance metrics. Here's a summary of its functions:

1. [**check_sherpa_status**](../handlers/default/handler_utils.py##check_sherpa_status): This function retrieves the `sherpa_heartbeat_interval` from `fm_config` and identifies stale_sherpa_status based on the `updated_at` timestamp is less than time of now minus `sherpa_heartbeat_interval` or it's none. If a stale_sherpa_status is not disabled,then  disabled it. If the mode is not 'disconnected', the mode is set to 'disconnected', and the change is recorded.

2. [**delete_notifications**](../handlers/default/handler_utils.py#delete-notifications): This function retrieves all notifications and evaluates them based on their creation time and compute timeout on the basis of log_level. Repetitive notifications have their timeout set to `repetition_freq`. Notifications that have exceeded their timeout or are of the type 'stale_alert_or_action' and originate from the 'dispatch_button' module are deleted, along with any notifications created an hour ago.

3. [**record_cpu_perf**](../handlers/default/handler_utils.py#record_cpu_perf): This function converts system performance data into a DataFrame and appends it to a CSV file located at `static/data_backup/sys_perf.csv`.

4. [**record_rq_perf**](../handlers/default/handler_utils.py#record_rq_perf): This function converts RQ performance data into a DataFrame and appends it to a CSV file located at `static/data_backup/rq_perf.csv`.