"""Some basic shorts for handling dates."""

from datetime import date, datetime, timedelta
from pathlib import Path


class DateHelper:
    """
    Class for simplyify date operations.

    This class provides static methods to handle date formatting, parsing, and calculations. It defaults to the "YYYY-MM-DD" format for date strings, but this can be overridden by passing a different format string.
    It also handles timezone-aware dates by using the local timezone of the system when parsing and formatting dates.
    """

    @staticmethod
    def format_date(date_obj: date, date_format: str = "%Y-%m-%d") -> str | None:
        """
        Format a date object to a string.

        Args:
            date_obj (date): The date object to format.
            date_format (str, optional): The format string to use for formatting the date.

        Returns:
            date_str (str): The formatted date string, or None if date_obj is None.
        """
        if date_obj is None:
            return None
        return date_obj.strftime(date_format)

    @staticmethod
    def parse_date(date_str: str, date_format: str = "%Y-%m-%d") -> date | None:
        """
        Parse a date string to a date object.

        Args:
            date_str (str): The date string to parse.
            date_format (Optional[str], optional): The format string to use for parsing the date. Defaults to "%Y-%m-%d".

        Returns:
            date_obj (date): A date object representing the parsed date, or None if date_str is empty.
        """
        local_tz = datetime.now().astimezone().tzinfo
        if not date_str:
            return None
        dt = datetime.strptime(date_str, date_format).replace(tzinfo=local_tz)
        return dt.date()

    @staticmethod
    def days_between(start_date: date, end_date: date) -> int | None:
        """
        Calculate the number of days between two date objects.

        Args:
            start_date (date): The start date.
            end_date (date): The end date.

        Returns:
            difference (int): The number of days between the two dates, or None if either date is None.
        """
        if start_date is None or end_date is None:
            return None
        return (end_date - start_date).days

    @staticmethod
    def add_days(start_date: date, days: int) -> date | None:
        """
        Add days to a date object.

        Args:
            start_date (date): The date to which days will be added.
            days (int): The number of days to add.

        Returns:
            date: A new date object with the added days, or None if start_date or days is None.

        """
        if start_date is None or days is None:
            return None
        return start_date + timedelta(days=days)

    @staticmethod
    def is_valid_date(date_str: str, date_format: str = "%Y-%m-%d") -> bool:
        """
        Check if a date string is valid according to the specified format.

        Args:
            date_str (str): The date string to check.
            date_format (Optional[str], optional): The format string to use for checking the date. Defaults to "%Y-%m-%d".

        Returns:
            result (bool): True if the date string is valid, False otherwise.
        """
        local_tz = datetime.now().astimezone().tzinfo
        try:
            datetime.strptime(date_str, date_format).replace(tzinfo=local_tz)
        except ValueError:
            return False
        else:
            return True

    @staticmethod
    def today() -> date:
        """
        Get today's date.

        Returns:
            result (date): Today's date as a date object, using the local timezone.
        """
        local_tz = datetime.now().astimezone().tzinfo
        return datetime.now(tz=local_tz).date()

    @staticmethod
    def today_add_days(days: int) -> date:
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
    def get_file_date(file_path: str | Path) -> date | None:
        """
        Get the last modified date of a file.

        Args:
            file_path (str | Path): Path to the file. Cane be a string or a Path object.

        Returns:
            date_obj (date): The last modified date of the file as a date object, or None if the file does not exist.
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        if not file_path.exists():
            return None

        local_tz = datetime.now().astimezone().tzinfo
        return datetime.fromtimestamp(file_path.stat().st_mtime, tz=local_tz).date()
