"""Manual testing code for the sc_utility libraries. Should not be included in the distrbution."""

import datetime as dt
import platform
import sys

from config_schemas import ConfigSchema
from sc_utility import (
    CSVReader,
    SCConfigManager,
    SCLogger,
)

CONFIG_FILE = "test_config.yaml"


def update_csv():
    csv_file_name = "test_csv.csv"

    header_config = [
        {
            "name": "Symbol",
            "type": "str",
            "match": True,
            "sort": 2,
        },
        {
            "name": "Date",
            "type": "date",
            "format": "%Y-%m-%d",
            "match": True,
            "sort": 1,
            "minimum": None,
        },
        {
            "name": "Name",
            "type": "str",
        },
        {
            "name": "Currency",
            "type": "str",
        },
        {
            "name": "Price",
            "type": "float",
            "format": ".2f",
        },
    ]

    extra_data = [
        {
            "Symbol": "AAPL",
            "Date": dt.date(2023, 10, 1),
            "Name": "Apple Inc.",
            "Currency": "USD",
            "Price": 150.00,
        },
        ]

    # Create an instance of the CSVReader class
    try:
        csv_reader = CSVReader(csv_file_name, header_config)
    except (ImportError, TypeError, ValueError) as e:
        print(e, file=sys.stderr)
        return

    csv_reader.update_csv_file(extra_data)


def main():
    """Main function to run the example code."""
    print(f"Hello from sc-utility running on {platform.system()}")

    # Get our default schema, validation schema, and placeholders
    schemas = ConfigSchema()

    # Initialize the SC_ConfigManager class
    try:
        config = SCConfigManager(
            config_file=CONFIG_FILE,
            default_config=schemas.default,
            validation_schema=schemas.validation,
            placeholders=schemas.placeholders
        )
    except RuntimeError as e:
        print(f"Configuration file error: {e}", file=sys.stderr)
        return

    # Initialize the SC_Logger class
    try:
        logger_settings = config.get_logger_settings()
        logger = SCLogger(logger_settings)
    except RuntimeError as e:
        print(f"Logger initialisation error: {e}", file=sys.stderr)
        return
    logger.log_message("This is a test message at the summary level.", "summary")

    # Setup email
    email_settings = config.get_email_settings()
    if email_settings is not None:
        logger.register_email_settings(email_settings)
        assert logger.send_email("Hello world", "Hello world from sc-utility example code.", test_mode=True), "Sending text string email."
        logger.send_email("sc_utility test - main()", "This is a test email.")

    update_csv()

    # See if we have a fatal error from a previous run
    if logger.get_fatal_error():
        print("Prior fatal error detected.")
        logger.clear_fatal_error()


if __name__ == "__main__":
    main()
