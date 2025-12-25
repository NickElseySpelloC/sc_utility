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

CONFIG_FILE = "dev_testing/dev_testing_config.yaml"


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
    print(f"Shelly control initialized successfully: {shelly_control}")
    # print(f"{shelly_control.print_model_library(mode_str='brief')}")

    # logger.log_message(f"Device summaries:\n {shelly_control.print_device_status()}", "all")

    return shelly_control


def test_spello_control(config, logger):
    """Test function for Spello control."""
    device_identity = "Sydney Solar"
    output_identity = "Solar Pump Output"
    # meter_identity = "Solar Pump Meter"

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


def test_get_status(config, logger):
    """Test function for refresh status."""
    loop_delay = 1
    loop_count = 0
    max_loops = 4

    output_name = "Sydney Dev A O1"

    shelly_control = create_shelly_control(config, logger)
    assert shelly_control is not None, "Shelly control should be initialized."
    try:
        output = shelly_control.get_device_component("output", output_name)
    except RuntimeError as e:
        print(f"Error getting device: {e}", file=sys.stderr)
        sys.exit(1)
    except TimeoutError as e:
        print(f"Timeout error getting device: {e}", file=sys.stderr)
        sys.exit(1)
    else:
        while loop_count < max_loops:
            # Refresh the status of all devices
            shelly_control.refresh_all_device_statuses()

            output_state = output.get("State", False)

            print(f"{output_name} State: {output_state}.")

            time.sleep(loop_delay)
            loop_count += 1


def test_get_status_and_temp(config, logger):  # noqa: PLR0914
    """Test function for refresh status."""
    loop_delay = 5
    loop_count = 0
    max_loops = 20

    device_name = "Sydney Solar"
    pump_output_name = "Sydney Dev A O1"
    roof_probe_name = "Temp Roof"
    pool_probe_name = "Temp Pool Water"

    shelly_control = create_shelly_control(config, logger)
    assert shelly_control is not None, "Shelly control should be initialized."
    try:
        device = shelly_control.get_device(device_name)
        pump_output = shelly_control.get_device_component("output", pump_output_name)
        roof_probe = shelly_control.get_device_component("temp_probe", roof_probe_name)
        pool_probe = shelly_control.get_device_component("temp_probe", pool_probe_name)
        internal_probe = shelly_control.get_device_component("temp_probe", device_name)
    except RuntimeError as e:
        print(f"Error getting device: {e}", file=sys.stderr)
        sys.exit(1)
    except TimeoutError as e:
        print(f"Timeout error getting device: {e}", file=sys.stderr)
        sys.exit(1)
    else:
        while loop_count < max_loops:
            # Refresh the status of all devices
            shelly_control.refresh_all_device_statuses()

            device_temp = device.get("Temperature", None)
            pump_state = pump_output.get("State")
            roof_probe_id = roof_probe.get("ProbeID", None)
            roof_probe_reading = roof_probe.get("Temperature", None)
            roof_time = roof_probe.get("LastReadingTime", None)

            pool_probe_id = pool_probe.get("ProbeID", None)
            pool_probe_reading = pool_probe.get("Temperature", None)
            pool_time = pool_probe.get("LastReadingTime", None)

            internal_probe_reading = internal_probe.get("Temperature", None)

            print(f"{device_name} Temperature: {device_temp}°C.")
            print(f"{pump_output_name} State: {pump_state}.")
            print(f"    {roof_probe_name} (ID: {roof_probe_id}) reading: {roof_probe_reading}°C last updated at {roof_time}")
            print(f"    {pool_probe_name} (ID: {pool_probe_id}) reading: {pool_probe_reading}°C last updated at {pool_time}")
            print(f"    {device_name} Internal Probe reading: {internal_probe_reading}°C")

            time.sleep(loop_delay)
            loop_count += 1


def test_shelly_loop(config: SCConfigManager, logger: SCLogger):
    """Test function for configuration file changes."""
    loop_delay = 1
    loop_count = 0
    max_loops = 4
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

    # Shut down the Shelly control to clean up resources
    shelly_control.shutdown()


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

    # test_spello_control(config, logger)

    # test_get_status(config, logger)

    # test_shelly_loop(config, logger)  # type: ignore[arg-type]

    test_get_status_and_temp(config, logger)

    # See if we have a fatal error from a previous run
    if logger.get_fatal_error():
        print("Prior fatal error detected.")
        logger.clear_fatal_error()


if __name__ == "__main__":
    main()
