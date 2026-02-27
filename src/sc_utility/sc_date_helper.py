"""Some basic shorts for handling dates."""

import datetime as dt
import json
from pathlib import Path
from warnings import deprecated

from sc_utility.sc_common import SCCommon

_LOCAL_TZ = dt.datetime.now().astimezone().tzinfo


class DateHelper:  # noqa: PLR0904
    """
    Class for simplyify date operations.

    This class provides static methods to handle date formatting, parsing, and calculations.

    This function supports a freeze time feature for testing purposes. See 'Freeze time feature' in the documentation below for more details.
    """

    @staticmethod
    def add(dt_obj: dt.date | dt.datetime, **kwargs) -> dt.date | dt.datetime | dt.time | None:
        """
        Add a timedelta to a date or datetime object.

        Args:
            dt_obj (date | datetime): The date or datetime object to which the timedelta will be added.
            **kwargs (keyword arguments): The keyword arguments to pass to the timedelta constructor (e.g., days=1, hours=2).

        Raises:
            TypeError: If dt_obj is not a date or datetime object, or if the keyword arguments are not valid for a timedelta.

        Returns:
            result (date | datetime): A new date or datetime object with the added timedelta, or None if dt_obj is None or not a date/datetime object.
        """
        if dt_obj is None or not isinstance(dt_obj, (dt.date, dt.datetime)):
            msg = f"Invalid data type passed DateHelper.add({dt_obj}). Expected a date or datetime object."
            raise TypeError(msg)

        try:
            return dt_obj + dt.timedelta(**kwargs)
        except TypeError as e:
            msg = f"Invalid keyword arguments for timedelta in DateHelper.add(dt_obj={dt_obj}, kwargs={kwargs}): {e}"
            raise TypeError(msg) from e

    @staticmethod
    def add_timezone(dt_obj: dt.datetime, tzinfo: dt.tzinfo | None = None) -> dt.datetime:
        """
        Add timezone information to a datetime object.

        Args:
            dt_obj (datetime): The datetime object to which the timezone information will be added.
            tzinfo (tzinfo): The timezone information to add to the datetime object. Defaults to the local timezone if not provided.

        Raises:
            TypeError: If dt_obj is not a date or datetime object, or if the keyword arguments are not valid for a timedelta.

        Returns:
            result (datetime): A new datetime object with the added timezone information, or None if dt_obj is None or not a datetime object.
        """
        if dt_obj is None or not isinstance(dt_obj, dt.datetime):
            msg = f"Invalid data type passed DateHelper.add_timezone({dt_obj}). Expected a datetime object."
            raise TypeError(msg)
        if tzinfo is None:
            tzinfo = DateHelper.get_local_timezone()
        return dt_obj.replace(tzinfo=tzinfo)

    @staticmethod
    def days_between(start_date: dt.date | dt.datetime, end_date: dt.date | dt.datetime) -> int | None:
        """
        Calculate the number of days between two date or datetime objects.

        Args:
            start_date (date): The start date.
            end_date (date): The end date.

        Returns:
            difference (int): The number of days between the two dates, or None if either date is None.
        """
        if start_date is None or end_date is None:
            return None
        if isinstance(start_date, dt.datetime):
            start_date = start_date.date()
        if isinstance(end_date, dt.datetime):
            end_date = end_date.date()
        return (end_date - start_date).days

    @staticmethod
    def extract(dt_str: str, format_str: str | None = None, hide_tz: bool = False) -> dt.date | dt.datetime | dt.time | None:
        """
        Extract a date or datetime from a string.

        format_str is optional. If not provided, the function will attempt to parse the string using the 'friendly date, datetime and time formats (see the format() function).
        If format_str is provided, it will be used to parse the string. If format_str is "ISO", the function will attempt to parse the string using the ISO 8601 format.
        If the string cannot be parsed using the provided format_str or the default formats, the function will return None.

        Args:
            dt_str (str): The string to extract the date, datetime, or time from.
            format_str (Optional[str], optional): The format string to use for parsing the date, datetime, or time. If None, the function will attempt to parse the string using common date and datetime formats.
            hide_tz (bool, optional): Whether to remove timezone information from the extracted datetime object. Defaults to False.

        Returns:
            result (date | datetime): A date or datetime object extracted from the string, or None if no date or datetime could be extracted.
        """
        return_dt_obj = None
        if format_str is not None:
            try:
                if format_str.upper() == "ISO":
                    return_dt_obj = dt.datetime.fromisoformat(dt_str)
                else:
                    return_dt_obj = dt.datetime.strptime(dt_str, format_str)  # noqa: DTZ007
            except ValueError:
                return None
        else:
            # Try parsing as datetime first, then date, then time
            try:
                return dt.datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S%z")
            except ValueError:
                pass
            try:
                return dt.datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")  # noqa: DTZ007
            except ValueError:
                pass
            try:
                return dt.datetime.strptime(dt_str, "%Y-%m-%d").date()  # noqa: DTZ007
            except ValueError:
                pass
            try:
                return dt.datetime.strptime(dt_str, "%H:%M:%S.%f").time()  # noqa: DTZ007
            except ValueError:
                pass
            try:
                return dt.datetime.strptime(dt_str, "%H:%M:%S").time()  # noqa: DTZ007
            except ValueError:
                pass

        if return_dt_obj is None:
            return None

        # If we have a datetime object with timezone info and hide_tz is True, remove the timezone info before returning the datetime object.
        if isinstance(return_dt_obj, dt.datetime):
            if hide_tz and return_dt_obj.tzinfo is not None:
                return_dt_obj = return_dt_obj.replace(tzinfo=None)
            if not hide_tz and return_dt_obj.tzinfo is None:
                local_tz = DateHelper.get_local_timezone()
                return_dt_obj = return_dt_obj.replace(tzinfo=local_tz)

        return return_dt_obj

    @staticmethod
    def format(dt_obj: dt.date | dt.datetime | dt.time, format_str: str | None = None, hide_tz: bool = True) -> str | None:
        """
        Format a date object to a string.

        If format_str is None, then dt_obj will use the default format according to it's type:
           date: %Y-%m-%d
           datetime: %Y-%m-%d %H:%M:%S
           time: %H:%M:%S
        The timezone will be included in the datetime string if it's included in dt_obj and hide_tz is False:
           datetime: %Y-%m-%d %H:%M:%S+11:00

        If format_str is "ISO" then the ISO 8601 format will be used.
            date: %Y-%m-%d
            datetime: %Y-%m-%dT%H:%M:%S[TZ]
            time: %H:%M:%S
        The timezone will be included in the datetime string if it's included in dt_obj.

        Args:
            dt_obj (date | datetime | time): The date, datetime, or time object to format.
            format_str (str, optional): The format string to use for formatting the date, datetime, or time.
            hide_tz (bool, optional): Whether to hide the timezone information in the formatted string. Only applies to datetime objects when format_str is None. Defaults to True.

        Returns:
            formatted_str: The datetime object formatted as a string, or None if dt_obj is None or an unsupported type.
        """
        if dt_obj is None:
            return None
        if not isinstance(dt_obj, (dt.date, dt.datetime, dt.time)):
            return None
        if format_str is None:
            if isinstance(dt_obj, dt.datetime):
                if dt_obj.tzinfo is not None and not hide_tz:
                    format_str = "%Y-%m-%d %H:%M:%S%:z"
                else:
                    format_str = "%Y-%m-%d %H:%M:%S"
            elif isinstance(dt_obj, dt.date):
                format_str = "%Y-%m-%d"
            elif isinstance(dt_obj, dt.time):
                format_str = "%H:%M:%S"

        elif format_str.upper() == "ISO":
            # Use .isoformat() instead of strftime for ISO format to ensure correct formatting of timezone-aware datetimes
            return dt_obj.isoformat()

        try:
            return dt_obj.strftime(format_str)
        except ValueError:
            return None

    @staticmethod
    def get_file_date(file_path: str | Path) -> dt.date | None:
        """
        Get the last modified date of a file.

        Args:
            file_path (str | Path): Path to the file. Can be a string or a Path object.

        Returns:
            date_obj (date): The last modified date of the file as a date object, or None if the file does not exist.
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        if not file_path.exists():
            return None

        local_tz = DateHelper.get_local_timezone()
        return dt.datetime.fromtimestamp(file_path.stat().st_mtime, tz=local_tz).date()

    @staticmethod
    def get_file_datetime(file_path: str | Path) -> dt.datetime | None:
        """
        Get the last modified datetime of a file.

        Args:
            file_path (str | Path): Path to the file. Can be a string or a Path object.

        Returns:
            datetime_obj (datetime): The last modified datetime of the file as a date object, or None if the file does not exist.
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        if not file_path.exists():
            return None

        local_tz = DateHelper.get_local_timezone()
        return dt.datetime.fromtimestamp(file_path.stat().st_mtime, tz=local_tz)

    @staticmethod
    def get_local_timezone() -> dt.tzinfo:
        """
        Get the local timezone of the system.

        Returns:
            tzinfo (tzinfo): The local timezone of the system.
        """
        return _LOCAL_TZ  # pyright: ignore[reportReturnType]

    @staticmethod
    def is_valid_date(date_str: str, format_str: str = "%Y-%m-%d") -> bool:
        """
        Check if a date or datetime string is valid according to the specified format.

        If format_str is "ISO", the function will attempt to parse the string using the ISO 8601 format.

        Args:
            date_str (str): The date string to check.
            format_str (Optional[str], optional): The format string to use for checking the date. Defaults to "%Y-%m-%d".

        Returns:
            result (bool): True if the date string is valid, False otherwise.
        """
        local_tz = DateHelper.get_local_timezone()
        try:
            if format_str.upper() == "ISO":
                dt.datetime.fromisoformat(date_str)
            else:
                dt.datetime.strptime(date_str, format_str).replace(tzinfo=local_tz)
        except ValueError:
            return False
        else:
            return True

    @staticmethod
    def is_valid_datetime(dt_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> bool:
        """
        Check if a date or datetime string is valid according to the specified format.

        If format_str is "ISO", the function will attempt to parse the string using the ISO 8601 format.

        Args:
            dt_str (str): The datetime string to check.
            format_str (Optional[str], optional): The format string to use for checking the datetime. Defaults to "%Y-%m-%d %H:%M:%S".

        Returns:
            result (bool): True if the datetime string is valid, False otherwise.
        """
        local_tz = DateHelper.get_local_timezone()
        try:
            if format_str.upper() == "ISO":
                dt.datetime.fromisoformat(dt_str)
            else:
                dt.datetime.strptime(dt_str, format_str).replace(tzinfo=local_tz)
        except ValueError:
            return False
        else:
            return True

    @staticmethod
    def is_valid_time(time_str: str, format_str: str = "%H:%M:%S") -> bool:
        """
        Check if a time string is valid according to the specified format.

        If format_str is "ISO", the function will attempt to parse the string using the ISO 8601 format.

        Args:
            time_str (str): The time string to check.
            format_str (Optional[str], optional): The format string to use for checking the time. Defaults to "%H:%M:%S".

        Returns:
            result (bool): True if the time string is valid, False otherwise.
        """
        local_tz = DateHelper.get_local_timezone()
        try:
            if format_str.upper() == "ISO":
                dt.datetime.fromisoformat(time_str)
            else:
                dt.datetime.strptime(time_str, format_str).replace(tzinfo=local_tz)
        except ValueError:
            return False
        else:
            return True

    @staticmethod
    def now(tzinfo: dt.tzinfo | None = None) -> dt.datetime:
        """
        Get today's date and time.

        Args:
            tzinfo (tzinfo, optional): The timezone information to use for getting the current datetime. Defaults to the local timezone if not provided.

        Returns:
            result (datetime): Today's date and time as a date object, using the local timezone.
        """
        if tzinfo is None:
            tzinfo = DateHelper.get_local_timezone()

        freeze_time = DateHelper._get_frozen_time()
        if freeze_time is not None:
            return freeze_time
        return dt.datetime.now(tz=tzinfo)

    @staticmethod
    def now_str(format_str: str | None = "%Y-%m-%d %H:%M:%S", tzinfo: dt.tzinfo | None = None) -> str:
        """
        Get the current time in string format.

        If format_str is "ISO" then the ISO 8601 format will be used.

        Args:
            format_str (Optional[str], optional): The format string to use for formatting the datetime.
            tzinfo (tzinfo, optional): The timezone information to use for getting the current datetime. Defaults to the local timezone if not provided.

        Returns:
            result (str): Current time as a formatted string, using the specified datetime format.
        """
        return DateHelper.format(DateHelper.now(tzinfo=tzinfo), format_str)  # type: ignore[call-arg]

    @staticmethod
    def now_utc() -> dt.datetime:
        """
        Get today's date and time in UTC.

        Returns:
            result (datetime): Today's date and time as a date object, using UTC timezone.

        Returns:
            result (datetime): Today's date and time as a date object, using the local timezone.
        """
        return DateHelper.now(tzinfo=dt.UTC)

    @staticmethod
    def today(tzinfo: dt.tzinfo | None = None) -> dt.date:
        """
        Get today's date.

        Args:
            tzinfo (tzinfo, optional): The timezone information to use for getting today's date. Defaults to the local timezone if not provided.

        Returns:
            result (date): Today's date as a date object, using the local timezone.
        """
        if tzinfo is None:
            tzinfo = DateHelper.get_local_timezone()
        return DateHelper.now(tzinfo=tzinfo).date()

    @staticmethod
    def today_add_days(days: int, tzinfo: dt.tzinfo | None = None) -> dt.date:
        """
        Get today's date ofset by days.

        Args:
            days (int): The number of days to offset from today. Can be positive or negative
            tzinfo (tzinfo, optional): The timezone information to use for getting today's date. Defaults to the local timezone if not provided.

        Returns:
            result (date): Today's date offset by the specified number of days.
        """
        return DateHelper.add(DateHelper.today(tzinfo=tzinfo), days=days)  # type: ignore[call-arg]

    @staticmethod
    def today_str(format_str: str | None = "%Y-%m-%d") -> str:
        """
        Get today's date in string format.

        If format_str is "ISO" then the ISO 8601 format will be used.

        Args:
            format_str (Optional[str], optional): The format string to use for formatting the date.

        Returns:
            result (str): Today's date as a formatted string, using the specified date format.
        """
        return DateHelper.format(DateHelper.today(), format_str)  # type: ignore[call-arg]

    @staticmethod
    def today_utc() -> dt.date:
        """
        Get today's date in UTC.

        Returns:
            result (date): Today's date as a date object, using UTC timezone.

        Returns:
            result (datetime): Today's date and time as a date object, using the local timezone.
        """
        return DateHelper.today(tzinfo=dt.UTC)

    @staticmethod
    def remove_timezone(dt_obj: dt.datetime) -> dt.datetime:
        """
        Remove timezone information from a datetime object.

        Args:
            dt_obj (datetime): The datetime object from which the timezone information will be removed.

        Raises:
            TypeError: If dt_obj is not a date or datetime object.

        Returns:
            result (datetime): A new datetime object with the timezone information removed.
        """
        if dt_obj is None or not isinstance(dt_obj, dt.datetime):
            msg = f"Invalid data type passed DateHelper.remove_timezone({dt_obj}). Expected a datetime object."
            raise TypeError(msg)
        return dt_obj.replace(tzinfo=None)

    # ==================================== DEPRECATED FUNCTIONS ====================================

    @staticmethod
    @deprecated("Use add() instead")
    def add_days(start_date: dt.date | dt.datetime, days: int) -> dt.date | dt.datetime | None:
        """
        Add days to a date or datetime object.

        Args:
            start_date (date | datetime): The date/datetime to which days will be added.
            days (int): The number of days to add.

        Returns:
            result (date | datetime) : A new date or datetime object with the added days, or None if start_date or days is None.

        """
        if start_date is None or days is None:
            return None
        return start_date + dt.timedelta(days=days)

    @staticmethod
    @deprecated("Use format() instead")
    def format_date(date_obj: dt.date | dt.datetime, date_format: str = "%Y-%m-%d") -> str | None:
        """
        Format a date object to a string.

        Args:
            date_obj (date | datetime): The date or datetime object to format.
            date_format (str, optional): The format string to use for formatting the date or datetime.

        Returns:
            date_str (str): The formatted date string, or None if date_obj is None.
        """
        if date_obj is None:
            return None
        return date_obj.strftime(date_format)

    @deprecated("Use extract() instead")
    @staticmethod
    def parse_date(date_str: str, date_format: str = "%Y-%m-%d") -> dt.date | dt.datetime | None:
        """
        Parse a date string to a date or datetime object.

        Args:
            date_str (str): The date string to parse.
            date_format (Optional[str], optional): The format string to use for parsing the date. Defaults to "%Y-%m-%d".

        Returns:
            date_obj (date | datetime): A date or datetime object representing the parsed date_str, or None if date_str is empty.
        """
        local_tz = DateHelper.get_local_timezone()
        if not date_str:
            return None
        parsed_dt = dt.datetime.strptime(date_str, date_format).replace(tzinfo=local_tz)

        # If the date_format string conatins only date components (like "%Y-%m-%d"), return a date object.
        # If it contains time components (like "%Y-%m-%d %H:%M:%S"), return a datetime object.
        if "%H" in date_format or "%M" in date_format or "%S" in date_format:
            return parsed_dt
        return parsed_dt.date()

    # ==================================== INTERNAL FUNCTIONS ====================================

    @staticmethod
    def _get_frozen_time() -> dt.datetime | None:
        """
        See if we need to return a frozen time for testing purposes.

        If a frozen time is set, it will be returned instead of the current time. See the documentation for the freeze time feature for more details.

        Returns:
            result (datetime): The datetime to use instead of the current time.
        """
        return None

    @staticmethod
    def _find_freeze_time_file() -> dict:
        """
        Look for a file named "freeze_time.json" in the current working directory, project root folder or the logs folder, and return its contents as a dictionary.

        Returns:
            result (dict): The contents of the "freeze_time.json" file as a dictionary, or an empty dictionary if the file is not found.
        """
        current_dir = Path.cwd()
        project_root = SCCommon.get_project_root()
        logs_dir = project_root / "logs"
        for folder in [current_dir, project_root, logs_dir]:
            freeze_time_file = folder / "freeze_time.json"
            if freeze_time_file.exists():
                try:

                    with freeze_time_file.open() as f:
                        return json.load(f)
                except (OSError, json.JSONDecodeError):
                    return {}
        return {}
