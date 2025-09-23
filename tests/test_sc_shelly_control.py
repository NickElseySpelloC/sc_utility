"""pytest for ShellyControl class."""
import sys

from sc_utility import SCConfigManager, SCLogger, ShellyControl

# Remove the period if running this in the debugger
from .config_schemas import ConfigSchema

CONFIG_FILE = "tests/config.yaml"
DEVICE_CLIENTNAME = "Device Test 1"

print("Running test for ShellyCOntrol...")

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
    sys.exit(1)
else:
    assert config is not None, "ConfigManager should be initialized"


# Initialize the SC_Logger class
try:
    logger = SCLogger(config.get_logger_settings())
except RuntimeError as e:
    print(f"Logger initialisation error: {e}", file=sys.stderr)
    sys.exit(1)
else:
    assert logger is not None, "Logger should be initialized"

# Create the ShellyControl object
shelly_settings = config.get_shelly_settings()
assert shelly_settings is not None, "Shelly settings should be initialized"

# Initialize the SC_ShellyControl class
try:
    shelly_control = ShellyControl(logger, shelly_settings)  # type: ignore[call-arg]
except RuntimeError as e:
    print(f"Shelly control initialization error: {e}", file=sys.stderr)
    sys.exit(1)
else:
    assert shelly_control is not None, "ShellyControl should be initialized"


def test_get_device():
    """Test function for Shelly control."""
    assert shelly_control is not None, "ShellyControl should be initialized"
    try:
        device = shelly_control.get_device(DEVICE_CLIENTNAME)
    except RuntimeError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    else:
        assert device is not None, f"Device {DEVICE_CLIENTNAME} should be found"
        assert isinstance(device, dict), "Device should be a dictionary"
        assert device.get("Index") == 0, "Device Index should be 0"
        assert device.get("ClientName") == DEVICE_CLIENTNAME, f"Device identity should be {DEVICE_CLIENTNAME}"
        assert device.get("Model") == "Shelly2PMG3", "Device Model should be Shelly2PMG3"
        assert device.get("Inputs") == 2, "Device input count should be 2"
        assert device.get("Outputs") == 2, "Device output count should be 2"
        assert device.get("Meters") == 2, "Device meter  count should be 2"


def test_get_device_information():
    """Test function for Shelly control."""
    assert shelly_control is not None, "ShellyControl should be initialized"
    try:
        device = shelly_control.get_device(DEVICE_CLIENTNAME)
        device_info = shelly_control.get_device_information(device)
    except RuntimeError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    else:
        assert device_info is not None, f"Device {DEVICE_CLIENTNAME} information should be found"
        assert isinstance(device_info, dict), f"Device {DEVICE_CLIENTNAME} information should be a dict"
        assert device_info.get("Model") == "Shelly2PMG3", "Device information should contain model information"
        assert len(device_info.get("Inputs")) == 2, "Device information should contain 2 inputs"  # type: ignore[call-arg]
        assert len(device_info.get("Outputs")) == 2, "Device information should contain 2 outputs"  # type: ignore[call-arg]
        assert len(device_info.get("Meters")) == 2, "Device information should contain 2 meters"  # type: ignore[call-arg]


def test_get_device_status():
    """Test function for Shelly control."""
    assert shelly_control is not None, "ShellyControl should be initialized"
    try:
        device = shelly_control.get_device(DEVICE_CLIENTNAME)
        result = shelly_control.get_device_status(device)
    except RuntimeError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    else:
        assert result is not None, f"Device {DEVICE_CLIENTNAME} status should be found"

    device_input = shelly_control.get_device_component("input", "Device 1.Input 1")
    assert device_input is not None, "Device input should be found"
    assert device_input.get("State") is not None, "Device input state should be found"
    assert isinstance(device_input.get("State"), bool), "Device input state should be a boolean"

    device_output = shelly_control.get_device_component("output", "Device 1.Output 2")
    assert device_output is not None, "Device output should be found"
    assert device_output.get("State") is not None, "Device output state should be found"
    assert isinstance(device_output.get("State"), bool), "Device output state should be a boolean"

    device_meter = shelly_control.get_device_component("meter", "Meter 1")  # Auto generated name
    assert device_meter is not None, "Device meter should be found"


def test_refresh_all_device_statuses():
    """Test function for refreshing all device statuses."""
    assert shelly_control is not None, "ShellyControl should be initialized"
    try:
        shelly_control.refresh_all_device_statuses()
    except RuntimeError as e:
        print(e, file=sys.stderr)
        sys.exit(1)


def test_is_device_online():
    """Test function for checking if a device is online."""
    assert shelly_control is not None, "ShellyControl should be initialized"
    try:
        is_online = shelly_control.is_device_online(DEVICE_CLIENTNAME)
    except RuntimeError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    else:
        assert is_online, f"Device {DEVICE_CLIENTNAME} should be online"


def test_print_device_status():
    """Test function for printing device status."""
    assert shelly_control is not None, "ShellyControl should be initialized"
    try:
        device_status = shelly_control.print_device_status(DEVICE_CLIENTNAME)
    except RuntimeError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    else:
        assert device_status is not None, f"Device {DEVICE_CLIENTNAME} status should be printed"
        assert isinstance(device_status, str), f"Device {DEVICE_CLIENTNAME} status should be a string"
        assert device_status.find("Generation: ") != -1, "Device status should contain generation information"


def test_print_model_library():
    """Test function for printing model library."""
    assert shelly_control is not None, "ShellyControl should be initialized"
    try:
        model_library = shelly_control.print_model_library(mode_str="brief")
    except RuntimeError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    else:
        assert model_library is not None, "Model library should be printed"
        assert isinstance(model_library, str), "Model library should be a string"
        assert model_library.find("Model: Shelly2PMG3") != -1, "Model library should contain Shelly2PMG3 model"


def test_change_output():
    """Test function for changing output state."""
    assert shelly_control is not None, "ShellyControl should be initialized"
    try:
        output_identity = "Device 1.Output 1"  # Example output identity
        output_obj = shelly_control.get_device_component("output", output_identity)
        current_state = output_obj["State"]
        result, did_change = shelly_control.change_output(output_identity, not current_state)
    except RuntimeError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    else:
        assert result, f"Output {output_identity} state changed successfully"
        assert did_change, f"Output {output_identity} state should have changed"
        # Optionally, you can check the new state of the output
        new_state = shelly_control.get_device_component("output", output_identity)["State"]
        assert new_state != current_state, "Output state should be changed"


# test_get_device()
# test_get_device_information()
# test_get_device_status()
# test_is_device_online()
# test_print_model_library()
# test_change_output()
