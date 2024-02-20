## Introduction ##

This directory contains periodic scripts called at [main.py](../main.py) as process, we have added decorator into most of them.  There are two types of decorators used:

1. [report_error](/utils/util.py#report_error) : This decorator runs the script within a try and except block and if an error occurs, it will log the error in a JSON format to the log file in `static/fm_errors` ([proc_exeption](/utils/util.py#proc_exeption)).

2. [proc_retry](/utils/util.py#proc_error) : This decorator triggers when an error occurs and retries the script until it no longer encounters any errors. 
