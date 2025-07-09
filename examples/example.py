"""Example code using the sc_utility libraries. Should not be included in the distrbution."""

import datetime as dt
import platform
import pprint
import sys

from example_config_schemas import ConfigSchema

from sc_utility import CSVReader, DateHelper, ExcelReader, SCConfigManager, SCLogger

CONFIG_FILE = "examples/example_config.yaml"
EXCEL_FILE = "examples/example_excel.xlsx"
CSV_FILE = "examples/example_csv.csv"


def update_csv():
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
        csv_reader = CSVReader(CSV_FILE, header_config)
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

    # Print a value from the sample config file
    print(f"API key = {config.get('AmberAPI', 'APIKey')}")

    # Initialize the SC_Logger class
    try:
        logger = SCLogger(config.get_logger_settings())
    except RuntimeError as e:
        print(f"Logger initialisation error: {e}", file=sys.stderr)
        return

    logger.log_message("This is a test message at the summary level.", "summary")

    # Setup email
    email_settings = config.get_email_settings()

    if email_settings is not None:
        logger.register_email_settings(email_settings)

        text_msg = "Hello world from sc-utility example code."
        if logger.send_email("Hello world", text_msg):
            logger.log_message("Email sent OK.", "detailed")

    # Use DateHelper to get the current date and time
    prior_date = DateHelper.today_add_days(-7)
    print(f"Prior date (7 days ago): {prior_date}")

    # Create an instance of ExcelReader
    print("Testing ExcelReader...")
    excel_reader = ExcelReader(EXCEL_FILE)

    # Extract a table
    try:
        table_data = excel_reader.extract_data(source_name="Table1", source_type="table")
    except ImportError as e:
        print(f"Error extracting table: {e}")
        sys.exit(1)
    else:
        print("Table data extracted successfully:\n")
        pprint.pprint(table_data)

    # Update a CSV file
    update_csv()

    # See if we have a fatal error from a previous run
    if logger.get_fatal_error():
        print("Prior fatal error detected.")
        logger.clear_fatal_error()


if __name__ == "__main__":
    main()
