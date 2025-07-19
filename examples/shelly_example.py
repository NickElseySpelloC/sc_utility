"""Example code using the sc_utility libraries. Should not be included in the distrbution."""

import platform
import sys

from example_config_schemas import ConfigSchema

from sc_utility import SCConfigManager, SCLogger, ShellyControl

CONFIG_FILE = "examples/example_config.yaml"


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
        logger = SCLogger(config.get_logger_settings())
    except RuntimeError as e:
        print(f"Logger initialisation error: {e}", file=sys.stderr)
        return

    shelly_settings = config.get_shelly_settings()

    if shelly_settings is None:
        print("No Shelly settings found in the configuration file.")
        return

    # Initialize the SC_ShellyControl class
    try:
        shelly_control = ShellyControl(logger, shelly_settings)  # type: ignore[arg-type]
    except RuntimeError as e:
        print(f"Shelly control initialization error: {e}", file=sys.stderr)
        return

    # Print the model library
    print(f"Print brief version of model library:\n {shelly_control.print_model_library(mode_str='brief')}")

    # Print the list of devices as configured in the config file
    print(f"Print all devices:\n {shelly_control.print_device_status()}")

    # Get a device
    device_identity = "Testing"
    try:
        device = shelly_control.get_device(device_identity)
    except (RuntimeError, TimeoutError) as e:
        print(e, file=sys.stderr)
    else:
        print(f"Device {device_identity} model: {device.get('Model', 'Unknown')}")
        print(f"Device {device_identity} is {'online' if device.get('Online', False) else 'offline'}.")

    # Change the output of a device
    output_identity = "Test Switch"
    output = shelly_control.get_device_component("output", output_identity)
    current_state = output["State"]
    result, did_change = shelly_control.change_output(output_identity, not current_state)
    print(f"Output {output_identity} changed: {did_change}, Result: {result}")


if __name__ == "__main__":
    main()
