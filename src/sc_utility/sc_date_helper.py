"""Some basic shorts for handling dates."""

import datetime as dt
from pathlib import Path


class DateHelper:
    """
    Class for simplyify date operations.

    This class provides static methods to handle date formatting, parsing, and calculations. It defaults to the "YYYY-MM-DD" format for date strings, but this can be overridden by passing a different format string.
    It also handles timezone-aware dates by using the local timezone of the system when parsing and formatting dates.
    """

    @staticmethod
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
        local_tz = dt.datetime.now().astimezone().tzinfo
        if not date_str:
            return None
        parsed_dt = dt.datetime.strptime(date_str, date_format).replace(tzinfo=local_tz)

        # If the date_format string conatins only date components (like "%Y-%m-%d"), return a date object.
        # If it contains time components (like "%Y-%m-%d %H:%M:%S"), return a datetime object.
        if "%H" in date_format or "%M" in date_format or "%S" in date_format:
            return parsed_dt
        return parsed_dt.date()

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
    def is_valid_date(date_str: str, date_format: str = "%Y-%m-%d") -> bool:
        """
        Check if a date or datetime string is valid according to the specified format.

        Args:
            date_str (str): The date string to check.
            date_format (Optional[str], optional): The format string to use for checking the date. Defaults to "%Y-%m-%d".

        Returns:
            result (bool): True if the date string is valid, False otherwise.
        """
        local_tz = dt.datetime.now().astimezone().tzinfo
        try:
            dt.datetime.strptime(date_str, date_format).replace(tzinfo=local_tz)
        except ValueError:
            return False
        else:
            return True

    @staticmethod
    def today() -> dt.date:
        """
        Get today's date.

        Returns:
            result (date): Today's date as a date object, using the local timezone.
        """
        local_tz = dt.datetime.now().astimezone().tzinfo
        return dt.datetime.now(tz=local_tz).date()

    @staticmethod
    def now() -> dt.datetime:
        """
        Get today's date and time.

        Returns:
            result (datetime): Today's date and time as a date object, using the local timezone.
        """
        local_tz = dt.datetime.now().astimezone().tzinfo
        return dt.datetime.now(tz=local_tz)

    @staticmethod
    def today_add_days(days: int) -> dt.date:
        """
        Get today's date ofset by days.

        Args:
            days (int): The number of days to offset from today. Can be positive or negative

        Returns:
            result (date): Today's date offset by the specified number of days.
        """
        date_today = DateHelper.today()
        return DateHelper.add_days(date_today, days)  # type: ignore[call-arg]

    @staticmethod
    def today_str(date_format: str | None = "%Y-%m-%d") -> str:
        """
        Get today's date in string format.

        Args:
            date_format (Optional[str], optional): The format string to use for formatting the date.

        Returns:
            result (str): Today's date as a formatted string, using the specified date format.
        """
        date_today = DateHelper.today()
        return DateHelper.format_date(date_today, date_format)  # type: ignore[call-arg]

    @staticmethod
    def now_str(datetime_format: str | None = "%Y-%m-%d %H:%M:%S") -> str:
        """
        Get the current time in string format.

        Args:
            datetime_format (Optional[str], optional): The format string to use for formatting the datetime.

        Returns:
            result (str): Current time as a formatted string, using the specified datetime format.
        """
        time_now = DateHelper.now()
        return DateHelper.format_date(time_now, datetime_format)  # type: ignore[call-arg]

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

        local_tz = dt.datetime.now().astimezone().tzinfo
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

        local_tz = dt.datetime.now().astimezone().tzinfo
        return dt.datetime.fromtimestamp(file_path.stat().st_mtime, tz=local_tz)
