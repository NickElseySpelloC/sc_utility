"""Manual testing code for the sc_utility libraries. Should not be included in the distrbution."""

import platform
import sys
from time import sleep

from config_schemas import ConfigSchema

from sc_utility import (
    SCCommon,
    SCConfigManager,
    SCLogger,
)

CONFIG_FILE = "test_config.yaml"


def test_reportable_issue(logger: SCLogger):
    # Log a reportable issue
    entity = "Output 1"
    issue = "Test issue"
    send_delay = 4  # seconds
    message = f"This is a test reportable issue for {entity} - {issue}"
    loop_target = 15

    logger.report_notifiable_issue(entity, issue, send_delay, message)

    # Now loop for 10 seconds, logging a message every 1 seconds
    for i in range(loop_target):
        print(f"Loop iteration {i + 1}/{loop_target}")
        sleep(1)
        if logger.report_notifiable_issue(entity, issue, send_delay, message):
            print("Email sent for reportable issue.")
            logger.clear_notifiable_issue(entity, issue)


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

    # Test internet connection
    if not SCCommon.check_internet_connection():
        logger.log_message("No internet connection detected.", "summary")

    # Setup email
    email_settings = config.get_email_settings()
    if email_settings is not None:
        logger.register_email_settings(email_settings)
        assert logger.send_email("Hello world", "Hello world from sc-utility example code.", test_mode=True), "Sending text string email."
        logger.send_email("sc_utility test - main()", "This is a test email.")

    # See if we have a fatal error from a previous run
    if logger.get_fatal_error():
        print("Prior fatal error detected.")
        logger.clear_fatal_error()

    test_reportable_issue(logger)


if __name__ == "__main__":
    main()
