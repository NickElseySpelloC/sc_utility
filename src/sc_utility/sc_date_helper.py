"""Some basic shorts for handling dates."""

from datetime import date, datetime, timedelta
from pathlib import Path


class DateHelper:
    @staticmethod
    def format_date(date_obj: date, date_format: str | None="%Y-%m-%d") -> str:
        """Format a date object to a string."""
        if date_obj is None:
            return None
        return date_obj.strftime(date_format)

    @staticmethod
    def parse_date(date_str: str, date_format: str | None="%Y-%m-%d") -> date:
        """Parse a date string to a date object."""
        local_tz = datetime.now().astimezone().tzinfo
        if not date_str:
            return None
        dt = datetime.strptime(date_str, date_format).replace(tzinfo=local_tz)
        return dt.date()

    @staticmethod
    def days_between(start_date: date, end_date: date) -> int:
        """Calculate the number of days between two date objects."""
        if start_date is None or end_date is None:
            return None
        return (end_date - start_date).days

    @staticmethod
    def add_days(start_date: date, days: int) -> date:
        """Add days to a date object."""
        if start_date is None or days is None:
            return None
        return start_date + timedelta(days=days)

    @staticmethod
    def is_valid_date(date_str: str, date_format: str | None="%Y-%m-%d") ->bool:
        """Check if a date string is valid according to the specified format."""
        local_tz = datetime.now().astimezone().tzinfo
        try:
            datetime.strptime(date_str, date_format).replace(tzinfo=local_tz)
        except ValueError:
            return False
        else:
            return True

    @staticmethod
    def today() -> date:
        """Get today's date."""
        local_tz = datetime.now().astimezone().tzinfo
        return datetime.now(tz=local_tz).date()

    @staticmethod
    def today_add_days(days: int) -> date:
        """Get today's date ofset by days."""
        date_today = DateHelper.today()
        return DateHelper.add_days(date_today, days)


    @staticmethod
    def today_str(date_format: str | None="%Y-%m-%d") -> str:
        """Get today's date in string format."""
        date_today = DateHelper.today()
        return DateHelper.format_date(date_today, date_format)

    @staticmethod
    def get_file_date(file_path: str | Path) -> date:
        """
        Get the last modified date of a file.

        param file_path: Path to the file. Cane be a string or a Path object.
        return: The last modified date of the file as a date object, or None if the file does not exist.
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        if not file_path.exists():
            return None

        local_tz = datetime.now().astimezone().tzinfo
        return datetime.fromtimestamp(file_path.stat().st_mtime, tz=local_tz).date()
