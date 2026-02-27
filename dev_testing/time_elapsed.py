"""Calculate seconds elapsed since January 1st, 2025."""

from datetime import UTC, datetime


def seconds_since_jan_1_2025() -> float:
    """Return the number of seconds that have elapsed since January 1st, 2025 00:00:00 UTC.

    Returns:
        float: Seconds elapsed since Jan 1, 2025 (can be negative if before that date)
    """
    jan_1_2025 = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
    now = datetime.now(UTC)
    delta = now - jan_1_2025
    return delta.total_seconds()


def main():
    """Demo the function."""
    seconds = seconds_since_jan_1_2025()
    print(f"Seconds elapsed since January 1st, 2025: {seconds:,.2f}")

    # Also show some human-readable conversions
    days = seconds / (24 * 3600)
    hours = seconds / 3600
    minutes = seconds / 60

    print("That's approximately:")
    print(f"  {days:,.2f} days")
    print(f"  {hours:,.2f} hours")
    print(f"  {minutes:,.2f} minutes")


if __name__ == "__main__":
    main()
