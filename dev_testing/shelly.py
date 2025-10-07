"""Manual testing code for the sc_utility libraries. Should not be included in the distrbution."""

import platform
import sys
import threading
import time

from config_schemas import ConfigSchema

from sc_utility import (
    DateHelper,
    SCCommon,
    SCConfigManager,
    SCLogger,
    ShellyControl,
)

CONFIG_FILE = "dev_testing_config.yaml"


def create_shelly_control(config, logger, wake_event: threading.Event | None = None):
    """Test function for Shelly control.

    Args:
        config (SCConfigManager): The configuration manager instance.
        logger (SCLogger): The logger instance.
        wake_event (threading.Event | None): Optional threading event to signal webhook events.

    Returns:
        ShellyControl | None: The initialized ShellyControl instance or None if initialization failed.
    """
    shelly_settings = config.get_shelly_settings()

    if shelly_settings is None:
        print("No Shelly settings found in the configuration file.")
        return None

    # Initialize the SC_ShellyControl class
    try:
        shelly_control = ShellyControl(logger, shelly_settings, wake_event)
    except RuntimeError as e:
        print(f"Shelly control initialization error: {e}", file=sys.stderr)
        return None
    # print(f"Shelly control initialized successfully: {shelly_control}")
    # print(f"{shelly_control.print_model_library(mode_str='brief')}")

    # logger.log_message(f"Device summaries:\n {shelly_control.print_device_status()}", "all")

    return shelly_control


def test_spello_control(config, logger):
    """Test function for Spello control."""
    device_identity = "Sydney Dev A"
    output_identity = "Sydney Dev A O1"
    # meter_identity = "Sydney Dev A M1"

    shelly_control = create_shelly_control(config, logger)
    assert shelly_control is not None, "Shelly control should be initialized."
    try:
        device = shelly_control.get_device(device_identity)
        device_status = shelly_control.get_device_status(device)
        if device_status:
            print(f"Device {device_identity} is online.")
        else:
            print(f"Device {device_identity} is offline or not found.")
    except RuntimeError as e:
        print(f"Error getting status for device {device_identity}: {e}", file=sys.stderr)
        sys.exit(1)
    except TimeoutError as e:
        print(f"Timeout error getting status for device {device_identity}: {e}", file=sys.stderr)
    else:
        logger.log_message(f"{device_identity} before output change:\n {shelly_control.print_device_status(device_identity)}", "all")

        output_obj = shelly_control.get_device_component("output", output_identity)
        is_online = shelly_control.is_device_online(device)
        shelly_control.get_device_status(device)
        current_state = output_obj.get("State", False)  # Default to False if State is not found
        print(f"#1 Output status for {output_identity}: Is Online: {is_online}, Current State: {current_state}")

        print("Waiting 7 seconds before changing the output state...")
        for i in range(7):
            time.sleep(1)  # Short delay to ensure the device is ready for the next command
            print(f"{i + 1}...", end="", flush=True)
        print()

        print("Attempting to change the output state...")
        shelly_control.change_output(output_identity, not current_state)

        # meter_obj = shelly_control.get_device_component("meter", meter_identity)
        # meter_reading = meter_obj.get("Energy", None)
        # print(f"Meter reading for {meter_identity}: {meter_reading}")

        is_online = shelly_control.is_device_online(device)
        shelly_control.get_device_status(device)
        current_state = output_obj.get("State", False)  # Default to False if State is not found
        print(f"#2 Output status for {output_identity}: Is Online: {is_online}, Current State: {current_state}")

        logger.log_message(f"{device_identity} after output change:\n {shelly_control.print_device_status(device_identity)}", "all")
        # print(shelly_control.print_device_status(device_identity))


def test_shelly_loop(config: SCConfigManager, logger: SCLogger):
    """Test function for configuration file changes."""
    loop_delay = 5
    loop_count = 0
    max_loops = 20
    wake_event = threading.Event()

    shelly_control = create_shelly_control(config, logger, wake_event)
    assert shelly_control is not None, "Shelly control should be initialized."

    # print(shelly_control.print_device_status())

    last_check = config.get_config_file_last_modified()
    print(f"Starting Shelly loop test. Logging level = {logger.file_verbosity}")
    while loop_count < max_loops:
        print(f"Checking for configuration file changes... (Loop {loop_count + 1}/{max_loops})")
        config_timestamp = config.check_for_config_changes(last_check)  # pyright: ignore[reportArgumentType]
        if config_timestamp:
            try:
                logger_settings = config.get_logger_settings()
                logger.initialise_settings(logger_settings)

                email_settings = config.get_email_settings()
                if email_settings is not None:
                    logger.register_email_settings(email_settings)

                shelly_settings = config.get_shelly_settings()
                if shelly_settings is not None:
                    shelly_control.initialize_settings(shelly_settings)

            except RuntimeError as e:
                print(f"Error reloading configuration: {e}", file=sys.stderr)
                sys.exit(1)
            else:
                print(f"Configuration file changed, reloaded config. Logging level = {logger.file_verbosity}")
                last_check = DateHelper.now()

        wake_event.wait(timeout=loop_delay)
        if wake_event.is_set():
            # We were woken by a webhook call
            event = shelly_control.pull_webhook_event()
            if event:
                print(f"Processing webhook event: {event.get('Event')}")
            wake_event.clear()
        loop_count += 1


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

    # Test internet connection
    if not SCCommon.check_internet_connection():
        logger.log_message("No internet connection detected.", "summary")

    test_spello_control(config, logger)

    # test_shelly_loop(config, logger)  # type: ignore[arg-type]

    # See if we have a fatal error from a previous run
    if logger.get_fatal_error():
        print("Prior fatal error detected.")
        logger.clear_fatal_error()


if __name__ == "__main__":
    main()
