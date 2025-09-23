"""pytest for DateHelper class."""
import datetime as dt
from pathlib import Path

from sc_utility import DateHelper

CONFIG_FILE = "tests/config.yaml"


def test_format_date():
    """Test format_date."""
    date_obj = dt.date(2025, 2, 1)
    formatted_date = DateHelper.format_date(date_obj)
    assert formatted_date == "2025-02-01", "Formatted date should be '2025-02-01'"


def test_parse_date():
    """Test parse_date."""
    date_str = "2025-02-04"
    parsed_date = DateHelper.parse_date(date_str)
    assert parsed_date == dt.date(2025, 2, 4), "Parsed date should be 2025-02-04"


def test_days_between():
    """Test calculating the number of days between two dates."""
    d1 = dt.date(2024, 1, 1)
    d2 = dt.date(2024, 1, 10)
    assert DateHelper.days_between(d1, d2) == 9, "Days between 2024-01-01 and 2024-01-10 should be 9"


def test_add_days():
    """Test adding days to a date."""
    start = dt.date(2024, 1, 1)
    result = DateHelper.add_days(start, 5)
    assert result == dt.date(2024, 1, 6), "Adding 5 days to 2024-01-01 should result in 2024-01-06"


def test_is_valid_date():
    """Test is_valid_date."""
    date_str = "2025-05-04"
    datetime_str = "2025-05-04 12:10:08"
    assert DateHelper.is_valid_date(date_str, "%Y-%m-%d"), "Date '2025-05-04' should be valid"
    assert DateHelper.is_valid_date(datetime_str, "%Y-%m-%d %H:%M:%S"), "Datetime '2025-05-04  12:10:08' should be valid"


def test_today():
    """Test today()."""
    local_tz = dt.datetime.now().astimezone().tzinfo
    today_date = dt.datetime.now(tz=local_tz).date()
    assert DateHelper.today() == today_date, "Today should return the current date"


def test_now():
    """Test today()."""
    local_tz = dt.datetime.now().astimezone().tzinfo
    time_now = dt.datetime.now(tz=local_tz)
    time_now_str = DateHelper.format_date(time_now, "%Y-%m-%d %H:%M")
    func_time_now_str = DateHelper.format_date(DateHelper.now(), "%Y-%m-%d %H:%M")
    assert time_now_str == func_time_now_str, "Now should return the current time"


def test_today_add_days():
    """Test today() with add_days."""
    today_date = DateHelper.today()
    future_date = DateHelper.add_days(today_date, 5)
    assert future_date == today_date + dt.timedelta(days=5), "Adding 5 days to today should return the correct date"


def test_today_str():
    """Test getting string representation of today's date."""
    today_str = DateHelper.today_str()
    formatted_today = DateHelper.format_date(DateHelper.today())
    assert today_str == formatted_today, "Today's string representation should match the formatted date"


def test_now_str():
    """Test getting string representation of the current time."""
    local_tz = dt.datetime.now().astimezone().tzinfo
    time_now = dt.datetime.now(tz=local_tz)
    time_str = DateHelper.format_date(time_now, "%Y-%m-%d %H:%M")
    formatted_now = DateHelper.format_date(DateHelper.now(), "%Y-%m-%d %H:%M")
    assert time_str == formatted_now, "Current time string representation should match the formatted datetime"


def test_get_file_date():
    """Test getting the file date."""
    file_path = Path(CONFIG_FILE)
    file_date = DateHelper.get_file_date(CONFIG_FILE)

    local_tz = dt.datetime.now().astimezone().tzinfo
    check_file_date = dt.datetime.fromtimestamp(file_path.stat().st_mtime, tz=local_tz).date()
    assert file_date == check_file_date, "File date should match the last modified date of the file"


def test_get_file_datetime():
    """Test getting the file datetime."""
    file_path = Path(CONFIG_FILE)
    file_date = DateHelper.get_file_datetime(CONFIG_FILE)

    local_tz = dt.datetime.now().astimezone().tzinfo
    check_file_datetime = dt.datetime.fromtimestamp(file_path.stat().st_mtime, tz=local_tz)
    assert file_date == check_file_datetime, "File datetime should match the last modified datetime of the file"
