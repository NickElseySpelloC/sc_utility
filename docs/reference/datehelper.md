# Date Helper

::: sc_utility.sc_date_helper.DateHelper

## Freeze time feature

This functionality will work as follows:

* Look for a freeze_time.json file in the project root folder.
* If freeze_time = valid datetime and one_time = false, then every call to now() will return the same datetime
* If freeze_time = valid datetime and one_time = true, then the first call to now() will return the specified datetime and each subsequent call will tick forward according to the normal clock.
* If offset_time_unit and offset_time_amount are set, then use timedelta to adjust the time. 
* If freeze_time and offset_time_amount are both set, freeze_time wins
* Other time / date relate functions now_str, today, etc.) will also honor the freeze time functionality

Example 1: Freeze the time forever at a specific date and time:
```json
{
    "freeze_time": "2026-02-21T12:34:56",
    "one_time": false
}
```

Example 2: Freeze the time and then tick forward aftre the first read of the file:
```json
{
    "freeze_time": "2026-02-21T12:34:56",
    "one_time": true
}
```

Example 3: Offset the current time by 3 hours
```json
{
    "offset_time_unit": "hours",
    "offset_time_amount": 3,
}
```

The freeze_time.json file must be writable. 

To accomdate example 2, freeze_time will be set to null after the one shot and replaced with offset_time_unit and offset_time_amount entries so that subsequent calls to now() will return a datetime that if offset from the true current time that the freeze_time was from the current time when the one shot pass was processed.