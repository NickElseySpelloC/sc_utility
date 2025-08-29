"""ShellyControl class for controlling Shelly Smart Switch devices."""
import json
import threading
import time
from http.server import ThreadingHTTPServer
from importlib import resources
from pathlib import Path

import requests

from sc_utility.sc_common import SCCommon
from sc_utility.sc_date_helper import DateHelper
from sc_utility.sc_logging import SCLogger
from sc_utility.webhook_server import _ShellyWebhookHandler

SHELLY_MODEL_FILE = "shelly_models.json"
DEFAULT_WEBHOOK_HOST = "0.0.0.0"  # noqa: S104
DEFAULT_WEBHOOK_PORT = 8787
DEFAULT_WEBHOOK_PATH = "/shelly/webhook"


class ShellyControl:
    """Control interface for Shelly Smart Switch devices."""

    def __init__(self, logger: SCLogger, device_settings: dict, app_wake_event: threading.Event | None = None):
        """Initializes the ShellySwitch object.

        Args:
            logger (SCLogger): The logger instance to use for logging messages.
            device_settings (dict): A dictionary containing the device, as returned by SCConfigManager.get_shelly_settings().
            app_wake_event (threading.Event | None): An optional event to wake the application when a webhook is received.

        Raises:
            RuntimeError: If the switch_settings configuration is invalid or incomplete or the model file cannot be found.
        """
        self.allow_debug_logging = device_settings.get("AllowDebugLogging", False)
        self.logger = logger
        self.response_timeout = 5   # Number of seconds to wait for a response from the switch
        self.retry_count = 1        # Number of times to retry a request
        self.retry_delay = 2        # Number of seconds to wait between retries

        self.webhook_enabled = False
        self.webhook_host = DEFAULT_WEBHOOK_HOST
        self.webhook_port = DEFAULT_WEBHOOK_PORT
        self.webhook_path = DEFAULT_WEBHOOK_PATH
        self.app_wake_event = app_wake_event
        self.webhook_event_queue = []

        self.devices = []           # List to hold multiple Shelly devices
        self.inputs = []            # List to hold multiple switch inputs, each one associated with a Shelly device
        self.outputs = []           # List to hold multiple relay outputs, each one associated with a Shelly device
        self.meters = []            # List to hold multiple energy meters, each one associated with a Shelly device

        # Load up the model library
        try:
            self._import_models()
        except RuntimeError as e:
            raise RuntimeError(e) from e

        # Now initialize the device settings
        self.initialize_settings(device_settings)

        # Start the webhook server if needed
        self._start_webhook_server()

    def _log_debug_message(self, message: str) -> None:
        """Logs a debug message.

        Args:
            message (str): The message to log.
        """
        if self.allow_debug_logging:
            self.logger.log_message(message, "debug")

    def _import_models(self) -> bool:
        """Imports the Shelly models from the shelly_models.json file.

        Raises:
            RuntimeError: If the JSON file cannot be loaded or is invalid.

        Returns:
            bool: True if the models were imported successfully, False otherwise.
        """
        try:
            files = resources.files("sc_utility")
            model_file = files / SHELLY_MODEL_FILE
            with model_file.open("r", encoding="utf-8") as file:
                self.models = json.load(file)
        except FileNotFoundError as e:
            error_msg = f"Could not find Shelly model file {SHELLY_MODEL_FILE} in the package."
            raise RuntimeError(error_msg) from e
        except json.JSONDecodeError as e:
            error_msg = f"JSON error loading Shelly models: {e}"
            raise RuntimeError(error_msg) from e
        else:
            self._log_debug_message(f"Imported Shelly models data from {model_file}.")
            return True

    def initialize_settings(self, device_settings: dict, refresh_status: bool | None = True):  # noqa: FBT001, FBT002
        """Initializes the Shelly devices using the provided settings.

        Args:
            device_settings (dict): A dictionary containing the device settings.
            refresh_status (bool | None): Whether to refresh the status of the devices.

        Raises:
            RuntimeError: If the device settings are invalid or incomplete.
        """
        # If switch_settings is provided, add switches from the configuration. Allow exception to be raised if the configuration is invalid.
        if device_settings:
            try:
                self._add_devices_from_config(device_settings)
            except RuntimeError as e:
                raise RuntimeError(e) from e

        # See if the devices are online
        self.is_device_online()

        # If requested, refresh the status of the devices
        if refresh_status:
            self.refresh_all_device_statuses()

        # Get the supported webhooks for each device if it's online
        self._set_supported_webhooks()

        # Install all the webhooks
        self._install_webhooks()

        # Finished
        self.logger.log_message("ShellyControl initialized successfully.", "detailed")

    def _set_supported_webhooks(self, selected_device: dict | None = None) -> None:
        """Set the SupportedWebhooks attrbute for each device using the Webhook.ListSupported API call.

        Args:
            selected_device (dict | None): The device to set supported webhooks for, or None to set for all devices.

        Raises:
            RuntimeError: If the Webhook.ListSupported API call fails.
        """
        for device in self.devices:
            if selected_device and device["Index"] != selected_device["Index"]:
                continue

            # Skip if device generation 1 (REST)
            if device.get("Protocol") != "RPC":
                continue

            # Skip if device is in simulation mode
            if device.get("Simulate", False):
                self._log_debug_message(f"Device {device.get('Name')} is in simulation mode, skipping determining supported webhooks.")
                continue

            # Skip if device is offline
            if not device.get("Online", False):
                self.logger.log_message(f"Device {device.get('Name')} is offline, unable to determine supported webhooks.", "warning")
                device["WebhookInstallPending"] = True
                continue

            try:
                # Now do a Webhook.ListSupported call and make sure our webhooks are supported
                payload = {
                    "id": 0,
                    "method": "Webhook.ListSupported"
                }
                result, result_data = self._rpc_request(device, payload)
                if not result:
                    self.logger.log_message(f"Failed to list supported webhooks for device {device.get('Name')}: {result_data}", "error")
                    continue
            except TimeoutError as e:
                error_msg = f"Timeout error listing supported webhooks for device {device.get('Name')}: {e}"
                self.logger.log_message(error_msg, "error")
                raise RuntimeError(error_msg) from e
            except RuntimeError as e:
                error_msg = f"Error installing listing supported webhooks for device {device.get('Name')}: {e}"
                self.logger.log_message(error_msg, "error")
                raise RuntimeError(error_msg) from e
            else:
                types_dict = result_data.get("types", {})
                device["SupportedWebhooks"] = [
                    {"name": k, **({"attrs": v["attrs"]} if "attrs" in v else {})}
                    for k, v in types_dict.items()
                ]

    def _install_webhooks(self, selected_device: dict | None = None):
        """Install all the default webhooks for each device.

        Args:
            selected_device (dict | None): The device to install webhooks for, or None to install for all devices.

        Raises:
            RuntimeError: If the webhook installation fails.
        """
        # If webhooks are disabled, return
        if not self.webhook_enabled:
            return

        for device in self.devices:
            if selected_device and device["Index"] != selected_device["Index"]:
                continue

            # If there are no supported webhooks, skip installation. This will also happen if the device is in simulation mode or offline.
            if not device["SupportedWebhooks"]:
                continue

            # Skip if device is offline
            if not device.get("Online", False):
                self.logger.log_message(f"Device {device.get('Name')} is offline, unable to install webhooks.", "warning")
                device["WebhookInstallPending"] = True
                continue

            # Clear all existing webhooks for this device
            payload = {
                "id": 0,
                "method": "Webhook.DeleteAll"
            }
            result, result_data = self._rpc_request(device, payload)
            if not result:
                self.logger.log_message(f"Failed to delete existing web hooks for device {device.get('Name')}: {result_data}", "error")
                continue

            # Now itterate through the inputs and outputs for each device and see which components have the Webhooks attribute set
            for component in self.inputs + self.outputs + self.meters:
                if component["DeviceIndex"] != device["Index"]:
                    continue

                # If the component does not have the Webhooks attribute, skip it
                if "Webhooks" not in component or not component["Webhooks"]:
                    continue

                # Get the list of default or configured events for this type of component
                configured_events = self._get_default_webhook_events_for_component(component)

                # Install each of these events
                for event in configured_events:
                    try:
                        self.install_webhook(event, component)
                    except RuntimeError as e:
                        error_msg = f"Error installing webhook for event {event} on component {component.get('Name')} of device {device.get('Name')}: {e}"
                        self.logger.log_message(error_msg, "error")
                        raise RuntimeError(error_msg) from e

    def _get_default_webhook_events_for_component(self, component: dict) -> list[str]:
        """Get the default or configure webhook events for a specific component.

        Args:
            component (dict): The component to get webhook events for.

        Returns:
            list[str]: A list of webhook events for the component.
        """
        component_type = component.get("ObjectType")
        if component_type not in {"input", "output", "meter"}:
            return []

        if component_type == "input":
            configured_events = self.default_webhook_events.get("Inputs", [])
            if configured_events:
                return configured_events
            return ["input.toggle_on", "input.toggle_off"]
        if component_type == "output":
            configured_events = self.default_webhook_events.get("Outputs", [])
            if configured_events:
                return configured_events
            return ["switch.on", "switch.off"]
        if component_type == "meter":
            configured_events = self.default_webhook_events.get("Meters", [])
            if configured_events:
                return configured_events
            return []
        return []

    def install_webhook(self, event: str, component: dict, url: str | None = None, additional_payload: dict | None = None) -> None:  # noqa: PLR0912
        """Install a webhook for the specified device and component.

        The function is used internally to install input and/or output webhooks that will be handled by the ShellyControl webhook
        handler server, but it can also be used to install additional webhooks that point to your own enpoint. If you use this
        function for custom webhooks, make sure your device supports the webhook event.

        The SupportedWebhooks attrbute of the device object lists the webhook events that each device supports (if any). See this page for documentation:
        https://shelly-api-docs.shelly.cloud/gen2/ComponentsAndServices/Webhook#webhookcreate

        You must have set the ShellyDevices: WebhooksEnabled configuration parameter to True for this function to install a webhook.

        The following arguments will automatically be added to the url string if not already provided:
          Event: The event type that triggered the webhook
          DeviceID: The ID attribute of the device that this webhook came from.
          ObjectType: The type of the component that this webhook came from. One of "input", "output", "meter"
          ComponentID: The ID attribute of the component that this webhook came from.
        For example:
           http://192.16.81.23:8787/shelly/webhook?Event=input.toggle_on&DeviceID=1&ObjectType=input&ComponentID=2

        Args:
            event (str): The event type to install the webhook for. This is case sensitive and must match the event type supported by the device
                         and componnent. For example "input.toggle_on". A RunTime error will be thrown is the event type is not supported.
            component (dict): The component object for the device component that you want to install the webhook on.
            url (str | None): The URL to send the webhook to. If None, the URL will be constructed using the webhook host, port, and path.
            additional_payload (dict | None): Additional key/value pairs to include in the webhook payload, for example active_between.

        Raises:
            RuntimeError: If the webhook installation fails.
        """
        # Get the device object
        device = self.get_device(component)

        # Look at the name keys in the device["SupportedWebhooks"] list of dicts and return if not found
        if not any(webhook.get("name") == event for webhook in device.get("SupportedWebhooks", [])):
            error_msg = f"Event {event} is not supported for component {component.get('Name')}"
            raise RuntimeError(error_msg)

        # Skip if device is offline
        if not device.get("Online", False):
            self.logger.log_message(f"Device {device.get('Name')} is offline, unable to install webhook {event}.", "warning")
            device["WebhookInstallPending"] = True
            return

        # Formulate the payload URL
        if url is None:
            payload_url = f"http://{self.webhook_host}:{self.webhook_port}{self.webhook_path}?Event={event}&DeviceID={device.get('ID')}&ObjectType={component.get('ObjectType')}&ComponentID={component.get('ID')}"
        else:
            payload_url = url
            # Now add the Event, DeviceIndex and ComponentIndex if not already present in the passed url

            def add_arg(url, arg):
                # If there are no URL arguments, start with '?', else use '&'
                if "?" not in url:
                    return url + "?" + arg
                return url + "&" + arg

            if "Event" not in url:
                payload_url = add_arg(payload_url, f"Event={event}")
            if "DeviceID" not in url:
                payload_url = add_arg(payload_url, f"DeviceID={device.get('ID')}")
            if "ObjectType" not in url:
                payload_url = add_arg(payload_url, f"ObjectType={component.get('ObjectType')}")
            if "ComponentID" not in url:
                payload_url = add_arg(payload_url, f"ComponentID={component.get('ID')}")

            # Now add any additional payload parameters
            if additional_payload:
                for key, value in additional_payload.items():
                    payload_url = add_arg(payload_url, f"{key}={value}")

        # Install the webhook
        try:
            error_msg = None
            payload = {
                "id": 0,
                "method": "Webhook.Create",
                "params": {
                    "cid": component.get("ComponentIndex"),
                    "enable": True,
                    "event": event,
                    "name": f"{component.get('Name')}: {event}",
                    "urls": [str(payload_url)]
                }
            }
            result, result_data = self._rpc_request(device, payload)
            if result:
                self._log_debug_message(f"Installed {event} webhook rev {result_data.get('rev')} for on component {component.get('Name')}")
            else:
                error_msg = f"Failed to create {event} webhook for component {component.get('Name')}: {result_data}"
                self.logger.log_message(error_msg, "error")
                # We will raise a RunTime error below

        except TimeoutError as e:
            error_msg = f"Timeout error installing web hooks for device {device.get('Name')}: {e}"
            self.logger.log_message(error_msg, "error")
            raise RuntimeError(error_msg) from e
        except RuntimeError as e:
            error_msg = f"Error installing web hooks for device {device.get('Name')}: {e}"
            self.logger.log_message(error_msg, "error")
            raise RuntimeError(error_msg) from e
        else:
            if error_msg:
                raise RuntimeError(error_msg)
            # Finally record what webhooks we have installed
            self._list_installed_webhooks(device)

    def _list_installed_webhooks(self, selected_device: dict | None = None) -> None:
        """List all installed webhooks for each device.

        Args:
            selected_device (dict | None): The device to list webhooks for. If None, list webhooks for all devices.

        Raises:
            RuntimeError: If the webhook enumeration fails.
        """
        # If the device doesn't support webhooks, no point in checkig to see what's installed
        for device in self.devices:
            if not device["SupportedWebhooks"]:
                continue

            if selected_device is not None and device != selected_device:
                continue

            try:
                payload = {
                    "id": 0,
                    "method": "Webhook.List"
                }
                result, result_data = self._rpc_request(device, payload)
                if not result:
                    self.logger.log_message(f"Failed to enumerate installed webhooks for device {device.get('Name')}: {result_data}", "error")
                    continue
            except TimeoutError as e:
                self.logger.log_message(f"Timeout error enumerating installed webhooks for device {device.get('Name')}: {e}", "error")
            except RuntimeError as e:
                error_msg = f"Error enumerating installed webhooks for device {device.get('Name')}: {e}"
                self.logger.log_message(error_msg, "error")
                raise RuntimeError(error_msg) from e
            else:
                device["InstalledWebhooks"] = result_data.get("hooks", [])

    def _start_webhook_server(self) -> ThreadingHTTPServer | None:
        """Start the webhook server in a background thread.

        Args:
            app_wake_event: A reference to the client application's wake event. This will be set when a webhook is received.

        Raises:
            RuntimeError: If the webhook server fails to start.

        Returns:
            ThreadingHTTPServer instance running the webhook server.
        """
        # If webhooks are disabled, return
        if not self.webhook_enabled:
            self._log_debug_message("Webhook server is disabled. Webhook server will not be started.")
            return None

        # If we are about to start the server, the self.app_wake_event must be valid
        if self.app_wake_event is None:
            error_msg = "app_wake_event is not set. Webhook server cannot be started."
            self.logger.log_message(error_msg, "error")
            raise RuntimeError(error_msg)

        try:
            server = ThreadingHTTPServer((self.webhook_host, self.webhook_port), _ShellyWebhookHandler)  # pyright: ignore[reportArgumentType]
            server.app_wake_event = self.app_wake_event  # type: ignore[attr-defined]
            server.controller = self  # type: ignore[attr-defined]
            server.webhook_path = self.webhook_path  # type: ignore[attr-defined]
            server.logger = self.logger  # type: ignore[attr-defined]

            t = threading.Thread(target=server.serve_forever, daemon=True, name="ShellyWebhookServer")
            t.start()
        except (RuntimeError, OSError, TypeError) as e:
            error_msg = f"Failed to start webhook server: {e}"
            self.logger.log_message(error_msg, "error")
            raise RuntimeError(error_msg) from e
        else:
            self._log_debug_message(f"Webhook server started on http://{self.webhook_host}:{self.webhook_port}{self.webhook_path}")
            return server

    def _push_webhook_event(self, args: dict) -> None:
        """Adds a webhook event to the queue for later processing. Used by the Wehhook listener.

        Args:
            args (dict): The arguments for the webhook event.
        """
        self._log_debug_message(f"Webhook event received: {args}")

        # Create a new event entry
        event_entry = {
            "timestamp": DateHelper.now(),
        }
        # Add each of the args, flattening single-element lists
        for k, v in args.items():
            if isinstance(v, list) and len(v) == 1:
                event_entry[k] = v[0]
            else:
                event_entry[k] = v  # pyright: ignore[reportArgumentType]

        # If the DeviceID is present, replace it with the actual device object
        if event_entry.get("DeviceID") is not None:
            device_id = int(event_entry.get("DeviceID"))  # pyright: ignore[reportArgumentType]
            device = self.get_device(device_id)
            if device is not None:
                event_entry.pop("DeviceID", None)
                event_entry["Device"] = device  # pyright: ignore[reportArgumentType]

        # If the ComponentID is present, replace it with the actual component object
        if event_entry.get("ObjectType") is not None and event_entry.get("ComponentID") is not None and event_entry.get("Device") is not None:
            # We need to figure out what type of component this is
            device = event_entry.get("Device")
            component_id = int(event_entry.get("ComponentID"))  # pyright: ignore[reportArgumentType]
            component_type = event_entry.get("ObjectType")
            component = self.get_device_component(component_type=component_type, component_identity=component_id)  # pyright: ignore[reportArgumentType]
            if component is not None:
                event_entry.pop("ObjectType", None)
                event_entry.pop("ComponentID", None)
                event_entry["Component"] = component  # pyright: ignore[reportArgumentType]

        self.webhook_event_queue.append(event_entry)

    def pull_webhook_event(self) -> dict | None:
        """Pulls a webhook event from the queue.

        Use this if your app has been interrupted by a webhook event (your app_wake_event was set).
        This will return the earliest webhook event that was received and remove it from the queue.

        Returns:
            dict | None: The next webhook event from the queue, or None if the queue is empty.
        """
        if self.webhook_event_queue:
            return self.webhook_event_queue.pop(0)
        return None

    def _add_devices_from_config(self, settings: dict) -> None:
        """Adds one or more Shelly devices from the provided configuration dictionary.

        If any devices have previously been added, they will be replaced by this configuration.

        Args:
            settings (dict): A dictionary containing the device settings, as returned by SCConfigManager.get_shelly_settings().

        Raises:
            RuntimeError: If the configuration is invalid or incomplete.
        """
        # First load the common settings
        self.allow_debug_logging = settings.get("AllowDebugLogging", False)
        self.response_timeout = settings.get("ResponseTimeout", self.response_timeout)   # Number of seconds to wait for a response from the switch
        self.retry_count = settings.get("RetryCount", self.retry_count)  # Number of times to retry a request
        self.retry_delay = settings.get("RetryDelay", self.retry_delay)  # Number of seconds to wait between retries
        self.ping_allowed = settings.get("PingAllowed", True)  # Whether to allow pinging the devices

        # Now the webhook settings
        self.webhook_enabled = settings.get("WebhooksEnabled", False)
        self.webhook_host = settings.get("WebhookHost", "0.0.0.0")  # noqa: S104
        self.webhook_port = settings.get("WebhookPort", 8787)
        self.webhook_path = settings.get("WebhookPath", "/shelly/webhook")
        self.default_webhook_events = settings.get("DefaultWebhooks", {})

        # Clear any existing devices, inputs, outputs, and meters
        self.devices.clear()
        self.inputs.clear()
        self.outputs.clear()
        self.meters.clear()

        # Now add each switch in the configuration
        try:
            for device in settings.get("Devices", []):
                self._add_device(device)
        except RuntimeError as e:
            raise RuntimeError(e) from e

    def _add_device(self, device_config: dict) -> None:
        """Adds a single switch to the list of switches.

        Args:
            device_config (dict): A dictionary containing a single Shelly device, as taken from the configuration file.

        Raises:
            RuntimeError: If the switch configuration is invalid or incomplete.
        """
        # Get the current size of the devices list to use as the index for the new device
        device_index = len(self.devices)

        # Create a device template and populate it with the device information from the models file.
        try:
            new_device = self._get_device_attributes(str(device_config.get("Model")))
        except RuntimeError as e:
            raise RuntimeError(e) from e

        # Now add the information from the passed device dictionary
        new_device["Index"] = device_index
        new_device["ClientName"] = device_config.get("Name", f"Shelly Device {device_index + 1}")
        new_device["ID"] = device_config.get("ID", device_index + 1)
        new_device["Simulate"] = device_config.get("Simulate", False)  # Default to False if not specified
        new_device["Label"] = f"{new_device['ClientName']} (ID: {new_device['ID']})"
        new_device["Hostname"] = device_config.get("Hostname")
        new_device["Port"] = device_config.get("Port", 80)  # Default port is 80

        # Validate that the device has an hostname if we are not in simulation mode
        if not new_device["Simulate"] and not new_device["Hostname"]:
            error_msg = f"Device {new_device['ClientName']} (ID: {new_device['ID']}) does not have an hostname configured. Cannot add device."
            raise RuntimeError(error_msg)

        # If a hostname is provided, validate that it is a valid IP address or hostname
        if new_device["Hostname"] and not SCCommon.is_valid_hostname(new_device["Hostname"]):
            error_msg = f"Device {new_device['ClientName']} (ID: {new_device['ID']}) has an invalid hostname: {new_device['Hostname']}. Cannot add device."
            raise RuntimeError(error_msg)

        # Validate that the client name is unique
        for existing_device in self.devices:
            if existing_device["ClientName"] == new_device["ClientName"]:
                error_msg = f"Device name {new_device['ClientName']} must be unique. Please choose a different name."
                raise RuntimeError(error_msg)

        # Validate that the ID is unique
        for existing_device in self.devices:
            if existing_device["ID"] == new_device["ID"]:
                error_msg = f"Device ID {new_device['ID']} must be unique. Please choose a different ID."
                raise RuntimeError(error_msg)

        # Validate that either an ID or a ClientName is provided
        if not new_device["ID"] and not new_device["ClientName"]:
            error_msg = "Device must have either an ID or a Name. Please provide one of these."
            raise RuntimeError(error_msg)

        # If we are in simulation mode, set the SimulationFile to the device's simulation file if provided
        if new_device["Simulate"]:
            file_name = new_device["ClientName"] or f"ShellyDevice_{new_device['ID']}"
            # Replace spaces with underscores and remove any non-alphanumeric characters
            file_name = "".join(c if c.isalnum() else "_" for c in file_name)
            file_name += ".json"  # Add the .json extension
            new_device["SimulationFile"] = SCCommon.select_file_location(file_name)

        # Add any additional custom key / value pairs defined in component_config that don't already exist in new_component
        new_device["customkeylist"] = []  # Initialize custom key list
        for key, value in device_config.items():
            if key not in new_device:
                new_device[key] = value
                new_device["customkeylist"].append(key)  # Track custom keys

        # Finally, add the device to the list of devices
        self.devices.append(new_device)

        # Add inputs, outputs, and meters for this device
        self._add_device_components(device_index, "input", device_config.get("Inputs"))
        self._add_device_components(device_index, "output", device_config.get("Outputs"))
        self._add_device_components(device_index, "meter", device_config.get("Meters"))

        # If in simuation mode, create the simulation file if it does not exist. Read the contents of the file if it does exist.
        self._import_device_information_from_json(new_device, create_if_no_file=True)

        # Finished
        self._log_debug_message(f"Added Shelly device {new_device['ClientName']}.")

    def _get_device_attributes(self, device_model: str) -> dict:
        """Creates a devie attrbutes object and populates the basic information on its model.

        See the shelly_control_objects.md file for the list of device attrbutes.

        Args:
            device_model (str): The model of the device.

        Raises:
            RuntimeError: If the model file is not loaded or the device model is not found in the models dictionary.

        Returns:
            dict: A dictionary containing the characteristics of the device, or None if the model is not supported.
        """
        # First lookup the model in the models dictionary - find the list item where "model" matches the device_model
        if not self.models:
            error_msg = f"Shelly model file {SHELLY_MODEL_FILE} not loaded. Cannot get device attributes."
            raise RuntimeError(error_msg)
        if not any(model_dict.get("model") == device_model for model_dict in self.models):
            error_msg = f"Device model {device_model} not found in the {SHELLY_MODEL_FILE} model file. Returning empty device attributes."
            raise RuntimeError(error_msg)
        # Find the model dictionary
        model_dict = next((model for model in self.models if model.get("model") == device_model), None)
        if model_dict is None:
            error_msg = f"Device model {device_model} not found in the {SHELLY_MODEL_FILE} model file. Returning empty device attributes."
            raise RuntimeError(error_msg)
        device = {
            "Index": len(self.devices),  # This will be set when the device is added to the devices list
            "Model": device_model,
            "ClientName": None,
            "ID": None,
            "ObjectType": "device",
            "Simulate": False,  # Default to False if not specified
            "SimulationFile": None,  # This will be set later if in simulation mode
            "ModelName": model_dict.get("name", "Unknown Model Name"),
            "Label": None,
            "URL": model_dict.get("url", None),
            "Hostname": None,
            "Port": 80,  # Default port is 80
            "Generation": model_dict.get("generation", 3),
            "Protocol": model_dict.get("protocol", "RPC"),
            "Inputs": model_dict.get("inputs", 1),
            "Outputs": model_dict.get("outputs", 1),
            "Meters": model_dict.get("meters", 0),
            "MetersSeperate": model_dict.get("meters_seperate", False),
            "TemperatureMonitoring": model_dict.get("temperature_monitoring", True),
            # The folowing will be set later when checking the switch status
            "Online": False,
            "MacAddress": None,
            "Temperature": None,
            "Uptime": None,
            "RestartRequired": None,
            "WebhookInstallPending": False,  # Set to True if device(s) need webhook installation because were offline at startup
            "SupportedWebhooks": [],
            "InstalledWebhooks": [],
            "customkeylist": [],  # Initialize custom key list for any custom attributes
            "TotalPower": 0.0,  # Total power consumption across all outputs
            "TotalEnergy": 0.0,  # Total energy consumption across all meters
        }
        # Do some basic validation of the device attributes
        if not device["MetersSeperate"] and device["Meters"] > 0 and device["Meters"] != device["Outputs"]:
            error_msg = f"Device {device['ClientName']} (ID: {device['ID']}) has a mismatch between the number of outputs ({device['Outputs']}) and meters ({device['Meters']}) when meters are not separate. Please check the configuration."
            raise RuntimeError(error_msg)

        self._log_debug_message(f"Retrieved Shelly model {device_model} ({device['ModelName']}) from models file.")
        return device

    def _add_device_components(self, device_index: int, component_type: str, component_config: list[dict] | None) -> None:  # noqa: PLR0912, PLR0915
        """Adds components (input, outputs, or meters) to an existing device.

        Args:
            device_index (int): The index of the device to which the component will be added.
            component_type (str): The type of component to add ('input', 'outputs', or 'meters').
            component_config (list[dict] | None): A list of the configured components for one device.

        Raises:
            RuntimeError: If the device index is invalid, component type is invalid, or the component configuration is incomplete.
        """
        if device_index < 0 or device_index >= len(self.devices):
            error_msg = f"Invalid device index {device_index}. Cannot add {component_type}."
            raise RuntimeError(error_msg)

        # Validate component type
        valid_types = {"input", "output", "meter"}
        if component_type not in valid_types:
            error_msg = f"Invalid component type '{component_type}'. Must be one of: {', '.join(valid_types)}."
            raise RuntimeError(error_msg)

        # Get the device from the list
        device = self.devices[device_index]

        # Set up component-specific configurations
        component_types_list = {
            "input": {
                "count_key": "Inputs",
                "storage_list": self.inputs,
                "name_prefix": "Input",
            },
            "output": {
                "count_key": "Outputs",
                "storage_list": self.outputs,
                "name_prefix": "Output",
            },
            "meter": {
                "count_key": "Meters",
                "storage_list": self.meters,
                "name_prefix": "Meter",
            }
        }

        component_type_config = component_types_list[component_type]
        expected_count = device[component_type_config["count_key"]]
        storage_list = component_type_config["storage_list"]

        # Validate the component configuration if provided
        if component_config is not None and (not isinstance(component_config, list) or len(component_config) != expected_count):
            error_msg = f"Invalid {component_type} configuration for device {device['ClientName']} (ID: {device['ID']}). Expected {expected_count} {component_type}, got {len(component_config)}."
            raise RuntimeError(error_msg)

        # Iterate through the number of components this device supports
        for component_idx in range(expected_count):
            # Create a new component dictionary
            new_component = self._new_device_component(device_index, component_type)

            # Populate it with the basic identity information
            if component_config is None:
                new_component["DeviceIndex"] = device_index
                new_component["ID"] = len(storage_list) + 1
                new_component["Name"] = f"{component_type_config['name_prefix']} {len(storage_list) + 1}"
                new_component["Webhooks"] = False
            else:
                new_component["DeviceIndex"] = device_index
                new_component["ID"] = component_config[component_idx].get("ID", len(storage_list) + 1)
                new_component["Name"] = component_config[component_idx].get("Name", f"{component_type_config['name_prefix']} {len(storage_list) + 1}")
                new_component["Webhooks"] = component_config[component_idx].get("Webhooks", False)

            # Set extra attributes
            new_component["ComponentIndex"] = component_idx
            if component_type == "input":
                new_component["State"] = False
            elif component_type == "output":
                new_component["State"] = False
                new_component["HasMeter"] = not device["MetersSeperate"]
            elif component_type == "meter":
                new_component["State"] = False
                new_component["OnOutput"] = not device["MetersSeperate"]

            # Add any additional custom key / value pairs defined in component_config that don't already exist in new_component
            new_component["customkeylist"] = []  # Initialize custom key list
            if component_config:
                for key, value in component_config[component_idx].items():
                    if key not in new_component:
                        new_component[key] = value
                        new_component["customkeylist"].append(key)  # Track custom keys

            # Validate that the name is unique
            for existing_component in storage_list:
                if existing_component["Name"] == new_component["Name"]:
                    error_msg = f"Device {component_type_config['name_prefix']} name {new_component['Name']} must be unique. Please choose a different name."
                    raise RuntimeError(error_msg)

            # Validate that the ID is unique
            for existing_component in storage_list:
                if existing_component["ID"] == new_component["ID"]:
                    error_msg = f"Device {component_type_config['name_prefix']} ID {new_component['ID']} must be unique. Please choose a different ID."
                    raise RuntimeError(error_msg)

            # Validate that either an ID or a Name is provided
            if not new_component["ID"] and not new_component["Name"]:
                error_msg = f"Device {component_type_config['name_prefix']} {len(storage_list)} must have either an ID or a Name. Please provide one of these."
                raise RuntimeError(error_msg)

            # Append the new component to the appropriate list
            storage_list.append(new_component)

    def _new_device_component(self, device_index: int, component_type: str) -> dict:
        """Creates a new device component (input, output, or meter) with the given parameters.

        Args:
            device_index (int): The index of the device to which the component will be added.
            component_type (str): The type of component to create ('input', 'outputs', or 'meters').

        Raises:
            RuntimeError: If the component type is invalid or if the device index is out of range.

        Returns:
            dict: A dictionary representing the new component with the relevent following keys:
                - DeviceIndex: The index of the device to which the component belongs.
                - ID: The ID of the component.
                - Name: The name of the component.
                - Additional attributes based on the component type.
        """
        # Validate component type
        valid_types = {"input", "output", "meter"}
        if component_type not in valid_types:
            error_msg = f"Invalid component type '{component_type}'. Must be one of: {', '.join(valid_types)}."
            raise RuntimeError(error_msg)

        # Get the device from the list
        device = self.devices[device_index]

        # Create a new component dictionary and populate it with the basic information
        new_component = {
            "DeviceIndex": device_index,
            "DeviceID": device["ID"],
            "ComponentIndex": None,
            "ObjectType": component_type,
            "ID": None,
            "Name": None,
            "Webhooks": False,
            "customkeylist": [],  # Initialize custom key list
        }

        # Add extra attributes based on the component type
        if component_type == "input":
            new_component["State"] = False
        elif component_type == "output":
            new_component["HasMeter"] = not self.devices[device_index]["MetersSeperate"]
            new_component["State"] = False
            new_component["Temperature"] = None
        elif component_type == "meter":
            new_component["OnOutput"] = not self.devices[device_index]["MetersSeperate"]
            new_component["Power"] = None
            new_component["Voltage"] = None
            new_component["Current"] = None
            new_component["PowerFactor"] = None
            new_component["Energy"] = None
        return new_component

    def get_device(self, device_identity: dict | int | str) -> dict:
        """Returns the device index for a given device ID or name.

        For device_identity you can pass:
        - A device object (dict) to retrieve it directly.
        - The device ID (int) to look it up by ID.
        - The device name (str) to look it up by name.
        - A component object (dict), which will return the parent device.

        Args:
            device_identity (dict | int | str): The identifier for the device.

        Raises:
            RuntimeError: If the device is not found in the list of devices.

        Returns:
            device (dict): The device object if found.
        """
        if isinstance(device_identity, dict):
            if device_identity.get("ObjectType") == "device":
                return device_identity  # If a dict is passed, return it directly
            return self.get_device(device_identity["DeviceID"])  # If a component dict is passed, return the parent device
        for device in self.devices:
            if device["ID"] == device_identity or device["ClientName"] == device_identity:
                return device

        error_msg = f"Device {device_identity} not found."
        raise RuntimeError(error_msg)

    def get_device_component(self, component_type: str, component_identity: int | str, use_index: bool | None = None) -> dict:  # noqa: FBT001
        """Returns a device component's index for a given component ID or name.

        Args:
            component_type (str): The type of component to retrieve ('input', 'output', or 'meter').
            component_identity (int | str): The ID or name of the component to retrieve.
            use_index (bool | None): If True, lookup by index instead of ID or name.

        Raises:
            RuntimeError: If the component is not found in the list.

        Returns:
            component(dict): The component index if found.
        """
        # Select the appropriate list based on the component type
        if component_type == "input":
            component_list = self.inputs
        elif component_type == "output":
            component_list = self.outputs
        elif component_type == "meter":
            component_list = self.meters
        else:
            error_msg = f"Invalid component type '{component_type}'. Must be one of: 'input', 'output', or 'meter'."
            raise RuntimeError(error_msg)

        for component in component_list:
            if use_index and component["ComponentIndex"] == component_identity:
                return component
            if component["ID"] == component_identity or component["Name"] == component_identity:
                return component

        error_msg = f"Device component {component_type} with identity {component_identity} not found."
        raise RuntimeError(error_msg)

    def is_device_online(self, device_identity: dict | int | str | None = None) -> bool:
        """See if a device is alive by pinging it.

        Returns the result and updates the device's online status. If we are in simulation mode, always returns True.

        Args:
            device_identity (Optional (dict | int | str | None), optional): The actual device object, device component object, device ID or device name of the device to check. If None, checks all device.

        Raises:
            RuntimeError: If the device is not found in the list of devices.

        Returns:
            result (bool): True if the device is online, False otherwise. If all devices are checked, returns True if all device are online.
        """
        found_offline_device = False
        try:
            selected_device = None
            if device_identity is not None:
                selected_device = self.get_device(device_identity)

            for index, device in enumerate(self.devices):
                if device["Simulate"] or not self.ping_allowed:
                    device["Online"] = True

                elif selected_device is None or selected_device["Index"] == index:
                    device_online = SCCommon.ping_host(device["Hostname"], self.response_timeout)
                    device["Online"] = device_online
                    if not device_online:
                        found_offline_device = True

                    self._log_debug_message(f"Shelly device {device['Label']} is {'online' if device_online else 'offline'}")

        except RuntimeError as e:
            raise RuntimeError(e) from e

        return not found_offline_device

    def print_device_status(self, device_identity: int | str | None = None) -> str:  # noqa: PLR0912, PLR0915
        """Prints the status of a device or all devices.

        Args:
            device_identity (Optional (int | str | None), optional): The ID or name of the device to check. If None, checks all devices.

        Raises:
            RuntimeError: If the device is not found in the list of devices.

        Returns:
            device_info (str): A string representation of the device status.
        """
        device_index = None
        return_str = ""
        try:  # noqa: PLR1702
            if device_identity is not None:
                selected_device = self.get_device(device_identity)
                device_index = selected_device["Index"]

            for index, device in enumerate(self.devices):
                if device_index is None or device_index == index:
                    return_str += f"{device['ClientName']} (ID: {device['ID']}) is {'online' if device['Online'] else 'offline'}.\n"
                    return_str += f"  Model: {device['ModelName']}\n"
                    return_str += f"  Simulation Mode: {device['Simulate']}\n"
                    return_str += f"  Hostname: {device['Hostname']}:{device['Port']}\n"
                    return_str += f"  Generation: {device['Generation']}\n"
                    return_str += f"  Protocol: {device['Protocol']}\n"

                    # Print custom device attributes
                    for custom_key in device.get("customkeylist", []):
                        return_str += f"  {custom_key}: {device[custom_key]}\n"

                    return_str += f"  Number of Inputs: {device['Inputs']}\n"
                    # Iterate through the inputs for this device
                    for device_input in self.inputs:
                        if device_input["DeviceIndex"] == index:
                            return_str += f"    - Index: {device_input['ComponentIndex']}, ID: {device_input['ID']}, Name: {device_input['Name']}, State: {device_input['State']}"

                            # Print custom input attributes
                            custom_attrs = []
                            for custom_key in device_input.get("customkeylist", []):
                                custom_attrs.append(f"{custom_key}: {device_input[custom_key]}")
                            if custom_attrs:
                                return_str += f", {', '.join(custom_attrs)}"
                            return_str += "\n"

                    return_str += f"  Number of Output Relays: {device['Outputs']}\n"
                    # Iterate through the outputs for this device
                    for device_output in self.outputs:
                        if device_output["DeviceIndex"] == index:
                            return_str += f"    - Index: {device_output['ComponentIndex']}, ID: {device_output['ID']}, Name: {device_output['Name']}, Has Metering: {device_output['HasMeter']}, State: {device_output['State']}, Temp.: {device_output['Temperature']}"

                            # Print custom output attributes
                            custom_attrs = []
                            for custom_key in device_output.get("customkeylist", []):
                                custom_attrs.append(f"{custom_key}: {device_output[custom_key]}")
                            if custom_attrs:
                                return_str += f", {', '.join(custom_attrs)}"
                            return_str += "\n"

                    return_str += f"  Number of Meters: {device['Meters']}\n"
                    # Iterate through the meters for this device
                    for device_meter in self.meters:
                        if device_meter["DeviceIndex"] == index:
                            return_str += f"    - Index: {device_meter['ComponentIndex']}, ID: {device_meter['ID']}, Name: {device_meter['Name']}, On Output: {device_meter['OnOutput']}, Power: {device_meter['Power']}, Voltage: {device_meter['Voltage']}, Current: {device_meter['Current']}, Power Factor: {device_meter['PowerFactor']}, Energy: {device_meter['Energy']}"

                            # Print custom meter attributes
                            custom_attrs = []
                            for custom_key in device_meter.get("customkeylist", []):
                                custom_attrs.append(f"{custom_key}: {device_meter[custom_key]}")
                            if custom_attrs:
                                return_str += f", {', '.join(custom_attrs)}"
                            return_str += "\n"

                    return_str += f"  Meters Separate: {device['MetersSeperate']}\n"
                    return_str += f"  Temperature Monitoring: {device['TemperatureMonitoring']}\n"
                    return_str += f"  Online: {device['Online']}\n"
                    return_str += f"  MAC Address: {device['MacAddress']}\n"
                    return_str += f"  Temperature: {device['Temperature']}°C\n"
                    return_str += f"  Total Power: {device['TotalPower']} W\n"
                    return_str += f"  Total Energy: {device['TotalEnergy']} kWh\n"
                    return_str += f"  Uptime: {device['Uptime']} seconds\n"

                    # Iterate through the supported webhooks
                    if device["SupportedWebhooks"]:
                        return_str += f"  Supported Webhooks: {len(device['SupportedWebhooks'])}\n"
                        for webhook in device["SupportedWebhooks"]:
                            return_str += f"    - {webhook.get('name')}\n"

                        # Iterate through the installed webhooks
                        if device["InstalledWebhooks"]:
                            return_str += f"  Installed Webhooks: {len(device['InstalledWebhooks'])}\n"
                            for webhook in device["InstalledWebhooks"]:
                                return_str += f"    - {webhook.get('name')}\n"
                        else:
                            return_str += "  No installed webhooks found.\n"
                    else:
                        return_str += "  Webhooks are not supported on this device.\n"

            return_str = return_str.strip()  # Remove trailing newline
        except RuntimeError as e:
            raise RuntimeError(e) from e
        return return_str

    def print_model_library(self, mode_str: str = "brief", model_id: str | None = None) -> str:
        """Prints the Shelly model library.

        Args:
            mode_str (str, optional): The mode of printing. Can be "brief" or "detailed". Defaults to "brief".
            model_id (Optional (str), optional): If provided, filters the models by this model name. If None, prints all models.

        Returns:
            library_info (str): A string representation of the Shelly model library.
        """
        if not self.models:
            return "No models loaded."

        return_str = "Shelly Model Library:\n"
        for model in self.models:
            if model_id is None or model["model"] == model_id:
                if mode_str == "brief":
                    return_str += f"Model: {model['model']}, Name: {model['name']}, URL: {model.get('url', 'N/A')}\n"
                elif mode_str == "detailed":
                    return_str += f"Model: {model['model']}\n"
                    return_str += f"  Name: {model['name']}\n"
                    return_str += f"  URL: {model.get('url', 'N/A')}\n"
                    return_str += f"  Generation: {model.get('generation', 'N/A')}\n"
                    return_str += f"  Protocol: {model.get('protocol', 'N/A')}\n"
                    return_str += f"  Inputs: {model.get('inputs', 'N/A')}\n"
                    return_str += f"  Outputs: {model.get('outputs', 'N/A')}\n"
                    return_str += f"  Meters: {model.get('meters', 'N/A')}\n"
                    return_str += f"  Meters Separate: {model.get('meters_seperate', 'N/A')}\n"
                    return_str += f"  Temperature Monitoring: {model.get('temperature_monitoring', 'N/A')}\n"
                else:
                    return_str += f"Unknown mode: {mode_str}. Please use 'brief' or 'detailed'.\n"
        return return_str.strip()

    def _rest_request(self, device: dict, url_args: str) -> tuple[bool, dict]:
        """Sends an REST GET request to a Shelly gen 1 device.

        Automatically retries the request if it fails for the configured number of retries.
        Pings the host first to check if it is online.

        Args:
            device (dict): The Shelly device to which the request will be sent.
            url_args (dict): The URL string to append to the GET request.

        Raises:
            RuntimeError: If there is an error sending the request or an error response is received.
            TimeoutError: If the request times out after the configured number of retries.

        Returns:
            tuple[bool, dict]: Returns True on success, False if the device is offline. If success, returns the response result data as a dictionary, None otherwise.
        """
        self._log_debug_message(f"Getting the status of device {device['Label']} at {device['Hostname']} via REST")

        # First ping the device to check if it is online
        if not self.is_device_online(device["ID"]):
            self.logger.log_message(f"Device {device['Label']} is offline. Cannot send REST request.", "warning")
            return False, {}

        url = f"http://{device['Hostname']}:{device['Port']}/{url_args}"
        headers = {
            "Content-Type": "application/json",
        }
        retry_count = 0
        fatal_error = None
        while retry_count <= self.retry_count and fatal_error is None:
            try:
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=self.response_timeout,
                )
                response.raise_for_status()  # Raise an error for bad responses (4xx or 5xx)
                if response.status_code != 200:
                    fatal_error = f"REST request to {device['Label']} returned status code {response.status_code}. Expected 200."
                    raise RuntimeError(fatal_error)
                response_data = response.json()
                if not response_data:
                    fatal_error = f"REST request to {device['Label']} returned empty result."
                    raise RuntimeError(fatal_error)

            except requests.exceptions.Timeout as e:    # Do an automatic retry if we timeout
                retry_count += 1
                if retry_count > self.retry_count:
                    fatal_error = f"Timeout error on REST call for device {device['Label']} after {self.retry_count} retries: {e}"
                    raise TimeoutError(fatal_error) from e
            except requests.exceptions.ConnectionError as e:  # Trap connection error - ConnectionError
                fatal_error = f"Connection error on REST call for device {device['Label']}: {e}"
                raise RuntimeError(fatal_error) from e
            except requests.exceptions.RequestException as e:
                fatal_error = f"Error fetching Shelly switch status: {e}"
                raise RuntimeError(fatal_error) from e
            else:
                return True, response_data

            # If we fall throught to here, we don't have a valid response, so we need to retry or raise an error
            if fatal_error is None:
                self._log_debug_message(f"Retrying REST request for device {device['Label']} (retry # {retry_count})")
                time.sleep(self.retry_delay)

        return False, {}   # Should never reach here, but just in case, return an empty dictionary

    def _rpc_request(self, device: dict, payload: dict) -> tuple[bool, dict]:
        """Sends an RPC request to a Shelly gen 2+ device.

        Automatically retries the request if it fails for the configured number of retries.
        Pings the host first to check if it is online.

        Args:
            device (dict): The Shelly device to which the request will be sent.
            payload (dict): The POST payload to send in the request.

        Raises:
            RuntimeError: If there is an error sending the request or an error response is received.
            TimeoutError: If the request times out after the configured number of retries.

        Returns:
            tuple[bool, dict]: Returns True on success, False if the device is offline. If success, returns the response result data as a dictionary, None otherwise.
        """
        self._log_debug_message(f"Getting the status of device {device['Label']} at {device['Hostname']} via RPC")

        # First ping the device to check if it is online
        if not self.is_device_online(device):
            self.logger.log_message(f"Device {device['Label']} is offline. Cannot send RPC request.", "warning")
            return False, {}

        url = f"http://{device['Hostname']}:{device['Port']}/rpc"
        headers = {
            "Content-Type": "application/json",
        }
        retry_count = 0
        fatal_error = None
        while retry_count <= self.retry_count and fatal_error is None:
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.response_timeout,
                )
                response.raise_for_status()  # Raise an error for bad responses (4xx or 5xx)
                if response.status_code == 401:  # Unauthorized
                    fatal_error = f"RPC request to {device['Label']} returned 401 unauthorised. Authorisation has not yet been implemented."
                    raise RuntimeError(fatal_error)
                if response.status_code != 200:
                    fatal_error = f"RPC request to {device['Label']} returned status code {response.status_code}. Expected 200."
                    raise RuntimeError(fatal_error)
                response_payload = response.json()
                response_data = response_payload.get("result", None)
                if not response_data:   # If no results are returned, check for an error message
                    shelly_error_message = response_payload.get("error", {}).get("message", None)
                    shelly_error_code = response_payload.get("error", {}).get("code", None)

                    if shelly_error_message:
                        fatal_error = f"RPC request to {device['Label']} returned error: {shelly_error_message} (code: {shelly_error_code})"
                    else:
                        fatal_error = f"RPC request to {device['Label']} returned empty result."
                    raise RuntimeError(fatal_error)

            except requests.exceptions.Timeout as e:    # Do an automatic retry if we timeout
                retry_count += 1
                if retry_count > self.retry_count:
                    fatal_error = f"Timeout error on RPC call for device {device['Label']} after {self.retry_count} retries: {e}"
                    raise TimeoutError(fatal_error) from e
            except requests.exceptions.ConnectionError as e:  # Trap connection error - ConnectionError
                fatal_error = f"Connection error on RPC call for device {device['Label']}: {e}"
                raise RuntimeError(fatal_error) from e
            except requests.exceptions.RequestException as e:
                fatal_error = f"Error fetching Shelly switch status: {e}"
                raise RuntimeError(fatal_error) from e
            else:
                return True, response_data

            # If we fall throught to here, we don't have a valid response, so we need to retry or raise an error
            if fatal_error is None:
                self._log_debug_message(f"Retrying RPC request for device {device['Label']} (retry # {retry_count})")
                time.sleep(self.retry_delay)

        return False, {}   # Should never reach here, but just in case, return an empty dictionary

    def get_device_status(self, device_identity: dict | int | str) -> bool:  # noqa: PLR0912, PLR0915
        """Gets the status of a Shelly device.

        Args:
            device_identity (dict | int | str): A device dict, or the ID or name of the device to check.

        Raises:
            RuntimeError: If the device is not found in the list of devices or if there is an error getting the status.
            TimeoutError: If the device is online (ping) but the request times out while getting the device status.

        Returns:
            result (bool): True if the device is online, False otherwise.
        """
        # Get the device object
        if isinstance(device_identity, dict):
            # If we are passed a device dictionary, use that directly
            device = device_identity
        else:
            try:
                device = self.get_device(device_identity)
                if not device:
                    self.logger.log_message(f"Device {device_identity} not found.", "error")
                    return False
            except RuntimeError as e:
                self.logger.log_message(f"Error getting device status for {device_identity}: {e}", "error")
                raise RuntimeError(e) from e

        # If device is in simulation mode, read from the json file
        if device["Simulate"]:
            self._import_device_information_from_json(device, create_if_no_file=True)
            return True  # Simulation mode always returns True

        try:
            if device["Protocol"] == "RPC":
                # Get the device status via RPC
                payload = {"id": 0, "method": "Shelly.GetStatus"}
                result, result_data = self._rpc_request(device, payload)

                # And if the meters are separate, we need to get the status of each of the meters as well
                # EM1.GetStatus gives use power, voltage, current
                # EM1Data.GetStatus gives us energy
                if device["MetersSeperate"]:
                    em_result_data = []
                    emdata_result_data = []
                    for meter_index in range(device["Meters"]):
                        payload = {"id": 0,
                                "method": "EM1.GetStatus",
                                "params": {"id": meter_index}
                                }
                        em_result, meter_data = self._rpc_request(device, payload)
                        if em_result:
                            em_result_data.append(meter_data)

                        payload = {"id": 0,
                                "method": "EM1Data.GetStatus",
                                "params": {"id": meter_index}
                                }
                        em_result, meter_data = self._rpc_request(device, payload)
                        if em_result:
                            emdata_result_data.append(meter_data)
            elif device["Protocol"] == "REST":
                # Get the device status via REST
                url_args = "status"
                result, result_data = self._rest_request(device, url_args)

                # For gen 1 we always expect the meters to be separate from the outputs
                if not device["MetersSeperate"]:
                    error_msg = f"Shelly model {device['Model']} (device {device['Label']}) is configured with combined meters & switches. No support for this combination yet. Please check the models file."
                    self.logger.log_message(error_msg, "error")
                    raise RuntimeError(error_msg)  # noqa: TRY301
            else:
                error_msg = f"Unsupported protocol {device['Protocol']} for device {device['Label']}. Only RPC and REST are supported."
                self.logger.log_message(error_msg, "error")
                raise RuntimeError(error_msg)  # noqa: TRY301
        except TimeoutError as e:
            self.logger.log_message(f"Timeout error getting device status for {device['Label']}: {e}", "error")
            raise TimeoutError(e) from e
        except RuntimeError as e:
            self.logger.log_message(f"Error getting status for device {device['Label']}: {e}", "error")
            raise RuntimeError(e) from e

        # Process the response payload
        if not result:  # Warning has already been logged if the device is offline
            return result

        # self.logger.log_message(f"REST response:\n {json.dumps(result_data, indent=2)}", "all")

        try:  # noqa: PLR1702
            if device["Protocol"] == "RPC":
                # Process the response payload for RPC protocol
                device["MacAddress"] = result_data.get("sys", {}).get("mac", None)  # MAC address
                device["Uptime"] = result_data.get("sys", {}).get("uptime", None)  # Uptime in seconds
                device["RestartRequired"] = result_data.get("sys", {}).get("restart_required", False)  # Restart required flag

                # # Itterate through the inputs, outputs, and meters for this device
                for device_input in self.inputs:
                    if device_input["DeviceIndex"] == device["Index"]:
                        component_index = device_input["ComponentIndex"]
                        device_input["State"] = result_data.get(f"input:{component_index}", {}).get("state", False)  # Input state
                for device_output in self.outputs:
                    if device_output["DeviceIndex"] == device["Index"]:
                        component_index = device_output["ComponentIndex"]
                        device_output["State"] = result_data.get(f"switch:{component_index}", {}).get("output", False)  # Output state
                        if device["TemperatureMonitoring"]:
                            device_output["Temperature"] = result_data.get(f"switch:{component_index}", {}).get("temperature", {}).get("tC", None)  # Temperature
                for device_meter in self.meters:
                    if device_meter["DeviceIndex"] == device["Index"]:
                        component_index = device_meter["ComponentIndex"]
                        if device["MetersSeperate"]:
                            if len(em_result_data) <= device["Meters"] or len(emdata_result_data) <= device["Meters"]:
                                error_msg = f"Device {device['Label']} is online, but meters are separate and at least one EM1.GetStatus RPC call failed. Cannot get meter status. Check models file."
                                self.logger.log_message(error_msg, "error")
                                raise RuntimeError(error_msg)  # noqa: TRY301
                            device_meter["Power"] = result_data.get("params", {}).get("act_power", None)
                            device_meter["Voltage"] = result_data.get("params", {}).get("voltage", None)
                            device_meter["Current"] = result_data.get("params", {}).get("current", None)
                            device_meter["PowerFactor"] = result_data.get("params", {}).get("pf", None)
                            device_meter["Energy"] = emdata_result_data[component_index].get("params", {}).get("total_act_energy", None)
                        else:
                            # Meters are on the switch. Make sure our component index matches the switch index
                            device_meter["Power"] = result_data.get(f"switch:{component_index}", {}).get("apower", None)  # Power in watts
                            device_meter["Voltage"] = result_data.get(f"switch:{component_index}", {}).get("voltage", None)
                            device_meter["Current"] = result_data.get(f"switch:{component_index}", {}).get("current", None)
                            device_meter["PowerFactor"] = result_data.get(f"switch:{component_index}", {}).get("pf", None)
                            device_meter["Energy"] = result_data.get(f"switch:{component_index}", {}).get("aenergy", {}).get("total", None)
            else:
                # Process the response payload for REST protocol
                device["MacAddress"] = result_data.get("mac", None)  # MAC address
                device["Uptime"] = result_data.get("uptime", None)  # Uptime in seconds
                device["RestartRequired"] = result_data.get("update", {}).get("has_update", False)  # Restart required flag
                if device["TemperatureMonitoring"]:
                    device["Temperature"] = result_data.get("temperature", None)  # May not be available

                # Itterate through the inputs, outputs, and meters for this device
                for device_input in self.inputs:
                    if device_input["DeviceIndex"] == device["Index"]:
                        component_index = device_input["ComponentIndex"]
                        device_input["State"] = result_data.get("inputs", []).get(component_index, {}).get("input", False)  # Input state
                for device_output in self.outputs:
                    if device_output["DeviceIndex"] == device["Index"]:
                        component_index = device_output["ComponentIndex"]
                        device_output["State"] = result_data.get("relays", [])[component_index].get("ison", False)  # Output state
                        if device["TemperatureMonitoring"]:
                            device_output["Temperature"] = device["Temperature"]    # Add to output for consistency
                for device_meter in self.meters:
                    if device_meter["DeviceIndex"] == device["Index"]:
                        component_index = device_meter["ComponentIndex"]
                        # In gen 1 the meter entries on switch devices list Shelly1PM are "meters" and on the EM1 devices they are "emeters"!
                        meter_key = "emeters" if len(result_data.get("emeters", [])) > 0 else "meters"

                        device_meter["Power"] = result_data.get(meter_key, [])[component_index].get("power", None)
                        device_meter["Voltage"] = result_data.get(meter_key, [])[component_index].get("voltage", None)
                        device_meter["Energy"] = result_data.get(meter_key, [])[component_index].get("total", None)

                        # Note that current and power factor are not available in the REST API for gen 1 devices, so we set them to None
                        device_meter["Current"] = None
                        device_meter["PowerFactor"] = None
        except (AttributeError, KeyError, RuntimeError) as e:
            error_msg = f"Error extracting status data for device {device['Label']}: {e}"
            self.logger.log_message(error_msg, "error")
            raise RuntimeError(error_msg) from e

        # If we have any energy meters, sum the power and energy readings for each meter and add them to the device
        self._calculate_device_totals(device)

        # Finally, install the default webhooks if we were offline and are now back
        if device["Online"] and device["WebhookInstallPending"]:
            self._set_supported_webhooks(device)

            # Install all the webhooks if not already done
            if self.does_device_have_webhooks(device) and not device["InstalledWebhooks"]:
                self._log_debug_message(f"{device['Label']} came back online, installing default webhooks")
                self._install_webhooks(device)

        self._log_debug_message(f"Device {device['Label']} status retrieved successfully.")

        return True

    def does_device_have_webhooks(self, device: dict) -> bool:
        """Returns True if the device has any webhooks installed, False otherwise.

        Args:
            device (dict): The Shelly device dictionary to check for webhooks.

        Returns:
            bool: True if the device has webhooks installed, False otherwise.
        """
        for component in self.inputs + self.outputs + self.meters:
            if component["DeviceIndex"] != device["Index"]:
                continue

            # If the component does not have the Webhooks attribute, skip it
            if "Webhooks" not in component or not component["Webhooks"]:
                continue

            return True  # This is our device and at least one of its components has Webhooks set to True

        return False

    def refresh_all_device_statuses(self) -> None:
        """Refreshes the status of all Shelly devices.

        This function iterates through all devices and updates their status by calling get_device_status.
        It also calculates the total power and energy consumption for each device.

        Raises:
            RuntimeError: If there is an error getting the status of any device.
        """
        for device in self.devices:
            try:
                self.get_device_status(device)
            except RuntimeError as e:
                self.logger.log_message(f"Error refreshing status for device {device['Label']}: {e}", "error")
                raise RuntimeError(e) from e

    def _calculate_device_totals(self, device: dict) -> None:
        """Calculates the total power and energy consumption for a device.

        This function iterates through the outputs and meters of the device to calculate the total power and energy consumption.
        It updates the device's TotalPower and TotalEnergy attributes.

        Args:
            device (dict): The Shelly device dictionary containing outputs and meters.
        """
        if device["Meters"] > 0:
            total_power = 0
            total_energy = 0
            for device_meter in self.meters:
                if device_meter["DeviceIndex"] == device["Index"]:
                    total_power += device_meter["Power"] if device_meter["Power"] is not None else 0
                    total_energy += device_meter["Energy"] if device_meter["Energy"] is not None else 0
            # Set the total power and energy readings on the device
            device["TotalPower"] = total_power
            device["TotalEnergy"] = total_energy

        # Set the Gen2+ device temperature if output temperature monitoring is available
        if device["TemperatureMonitoring"] and device["Outputs"] > 0:
            average_temperature = 0
            output_count = 0
            for device_output in self.outputs:
                if device_output["DeviceIndex"] == device["Index"] and device_output["Temperature"]:
                    output_count += 1
                    average_temperature += device_output["Temperature"]
            if output_count > 0:
                device["Temperature"] = average_temperature / output_count  # Average temperature across all outputs

    def change_output(self, output_identity: dict | int | str, new_state: bool) -> tuple[bool, bool]:  # noqa: FBT001
        """Change the state of a Shelly device output to on or off.

        Args:
            output_identity (dict | int | str): An output dict, or the ID or name of the device to check.
            new_state (bool): The new state to set the output to (True for on, False for off).

        Raises:
            RuntimeError: There was an error changing the device output state.
            TimeoutError: If the device is online (ping) but the state change request times out.

        Returns:
            result (bool): True if the output state was changed successfully, False if the device is offline.
            did_change (bool): True if the output state is different than before, False if it was already in the desired state.
        """
        # Get the device object
        if isinstance(output_identity, dict):
            # If we are passed a device dictionary, use that directly
            device_output = output_identity
        else:
            try:
                device_output = self.get_device_component("output", output_identity)
            except RuntimeError as e:
                self.logger.log_message(f"Error getting changing device output {output_identity}: {e}", "error")
                raise RuntimeError(e) from e

        # Get the device object
        device = self.devices[device_output["DeviceIndex"]]

        # Make a note of the current state before changing it
        current_state = device_output["State"]

        # If we are not in simulation mode
        if not device["Simulate"]:
            try:
                # First get the device status to ensure it is online
                if not self.get_device_status(device):
                    self.logger.log_message(f"Device {device['Label']} is offline. Cannot change output state.", "warning")
                    return False, False

                if device["Protocol"] == "RPC":
                    # Change the output via RPC
                    payload = {
                                "id": 0,
                                "method": "Switch.Set",
                                "params": {"id": device_output["ComponentIndex"],
                                        "on": new_state}
                                }
                    result, _result_data = self._rpc_request(device, payload)

                elif device["Protocol"] == "REST":
                    # Get the device status via REST
                    url_args = f"relay/{device_output['ComponentIndex']}?turn={'on' if new_state else 'off'}"
                    result, _result_data = self._rest_request(device, url_args)

                else:
                    error_msg = f"Unsupported protocol {device['Protocol']} for device {device['Label']}. Only RPC and REST are supported."
                    self.logger.log_message(error_msg, "error")
                    raise RuntimeError(error_msg)  # noqa: TRY301
            except TimeoutError as e:
                self.logger.log_message(f"Timeout error changing device output {output_identity} for device {device['Label']}: {e}", "error")
                raise TimeoutError(e) from e
            except RuntimeError as e:
                self.logger.log_message(f"Error changing device output {output_identity} for device {device['Label']}: {e}", "error")
                raise RuntimeError(e) from e

            # Process the response payload
            if not result:  # Warning has already been logged if the device is offline
                return result, False

        # If we get here, we were successful in changing the output state
        # Update the output state in the outputs list
        device_output["State"] = new_state

        # If in simulation mode, save the json file
        if device["Simulate"]:
            self._export_device_information_to_json(device)

        if new_state != current_state:
            self._log_debug_message(f"Device output {output_identity} on device {device['Label']} was changed to {'on' if new_state else 'off'}.")
            return True, True

        self._log_debug_message(f"Device output {output_identity} on device {device['Label']} is already {'on' if new_state else 'off'}. No change made.")
        return True, False

    def get_device_location(self, device_identity: dict | int | str) -> dict | None:
        """Gets the timezone and location of a Shelly device if available.

        Returns a dict in the following format:
           "tz": "Europe/Sofia",
           "lat": 42.67236,
           "lon": 23.38738

        Args:
            device_identity (dict | int | str): A device dict, or the ID or name of the device to check.

        Raises:
            RuntimeError: If the device is not found in the list of devices or if there is an error getting the status.
            TimeoutError: If the device is online (ping) but the request times out while getting the device status.

        Returns:
            location (dict | None): A dictionary containing the timezone and location of the device, or None if not available.
        """
        # Get the device object
        if isinstance(device_identity, dict):
            # If we are passed a device dictionary, use that directly
            device = device_identity
        else:
            try:
                device = self.get_device(device_identity)
                if not device:
                    self.logger.log_message(f"Device {device_identity} not found.", "error")
                    return None
            except RuntimeError as e:
                self.logger.log_message(f"Error getting device status for {device_identity}: {e}", "error")
                raise RuntimeError(e) from e

        # If device is in simulation mode, read from the json file
        if device["Simulate"]:
            # Return a fake location
            location = {
                "tz": "Europe/Sofia",
                "lat": 42.67236,
                "lon": 23.38738
            }
            return location

        if not device["Online"]:
            return None

        if device["Protocol"] != "RPC":
            return None

        try:
            payload = {"id": 0, "method": "Shelly.DetectLocation"}
            result, result_data = self._rpc_request(device, payload)
            if not result:
                self.logger.log_message(f"Failed to gett device location for device {device.get('Name')}: {result_data}", "error")
                return None
        except TimeoutError as e:
            self.logger.log_message(f"Timeout error getting device location for {device['Label']}: {e}", "error")
            raise TimeoutError(e) from e
        except RuntimeError as e:
            self.logger.log_message(f"Error getting location for device {device['Label']}: {e}", "error")
            raise RuntimeError(e) from e
        else:
            return result_data

    def get_device_information(self, device_identity: dict | int | str, refresh_status: bool = False) -> dict:  # noqa: FBT001, FBT002
        """Returns a consolidated copy of a Shelly device information as a single dictionary, including its inputs, outputs, and meters.

        Args:
            device_identity (dict | int | str): The device itself or an ID or name of the device to retrieve information for.
            refresh_status (bool, optional): If True, refreshes the device status before retrieving information. Defaults to False.

        Raises:
            RuntimeError: If the device is not found in the list of devices or if there is an error getting the status.

        Returns:
            device_info (dict): A dictionary containing the device's attributes, inputs, outputs, and meters.
        """
        try:
            device = self.get_device(device_identity)
            device_index = device["Index"]  # Get the index of the device
            if refresh_status:  # If refresh_status is True, get the latest status of the device
                self.get_device_status(device_identity)  # Ensure we have the latest status
        except RuntimeError as e:
            self.logger.log_message(f"Error getting device information for {device_identity}: {e}", "error")
            raise RuntimeError(e) from e

        # Create a consolidated view of the device's attributes
        device_info = device.copy()  # Create a copy of the device dictionary
        device_info["Inputs"] = [component_input for component_input in self.inputs if component_input["DeviceIndex"] == device_index]
        device_info["Outputs"] = [component_output for component_output in self.outputs if component_output["DeviceIndex"] == device_index]
        device_info["Meters"] = [component_meter for component_meter in self.meters if component_meter["DeviceIndex"] == device_index]

        return device_info

    def _export_device_information_to_json(self, device: dict) -> bool:
        """Exports device information to a JSON file.

        Args:
            device (dict): The device to export.

        Raises:
            RuntimeError: If the device is not found or if there is an error writing the file.

        Returns:
            bool: True if the export was successful, False otherwise.
        """
        # If we're not in simulation mode for this device, do nothing
        if not device.get("Simulate"):
            self._log_debug_message(f"Device {device['Label']} is not in simulation mode. Skipping export.")
            return False

        # Get the path to the JSON file
        file_path = device["SimulationFile"]
        if not isinstance(file_path, Path):
            error_msg = f"No simulation file path available for device {device['Label']} while in simulation mode"
            self.logger.log_message(error_msg, "error")
            raise RuntimeError(error_msg)  # noqa: TRY004

        try:
            # Get the device information
            device_info = self.get_device_information(device, refresh_status=False)

            # Ensure the directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Serialize to JSON with proper formatting
            with file_path.open("w", encoding="utf-8") as json_file:
                json.dump(device_info, json_file, indent=2, ensure_ascii=False, default=str)

        except RuntimeError as e:
            self.logger.log_message(f"Error exporting device information for {device['Label']}: {e}", "error")
            raise RuntimeError(e) from e
        except OSError as e:
            error_msg = f"Error writing device information to file {file_path}: {e}"
            self.logger.log_message(error_msg, "error")
            raise RuntimeError(error_msg) from e
        else:
            self._log_debug_message(f"Device information for {device['Label']} exported to {file_path}")
            return True

    def _import_device_information_from_json(self, device: dict, create_if_no_file: bool) -> bool:  # noqa: FBT001, PLR0912, PLR0915
        """Imports device information from a JSON file and updates the device attributes.

        While the JSON file will store everything provided by get_device_information(), this function
        will only update the device and components that are normally modified by a get_device_status call.

        Args:
            device (dict): The device to updated from json
            create_if_no_file (bool): If True, creates a new JSON file if it does not exist using _export_device_information_to_json()

        Raises:
            RuntimeError: If the file cannot be read, JSON is invalid, or device cannot be found/matched.

        Returns:
            bool: True if the import was successful, False otherwise.
        """
        # If we're not in simulation mode for this device, do nothing
        if not device.get("Simulate"):
            self._log_debug_message(f"Device {device['Label']} is not in simulation mode. Skipping import.")
            return False

        # Get the path to the JSON file
        file_path = device["SimulationFile"]
        if not isinstance(file_path, Path):
            error_msg = f"Not simulation file path available for device {device['Label']} while in simulation mode"
            self.logger.log_message(error_msg, "error")
            raise RuntimeError(error_msg)  # noqa: TRY004

        # Check if file exists
        if not file_path.exists():
            # If the file does not exist and create_if_no_file is True, export the device information to JSON
            if create_if_no_file:
                self._log_debug_message(f"JSON file {file_path} does not exist. Creating new file.")
                return self._export_device_information_to_json(device)
            error_msg = f"JSON file {file_path} does not exist and create_if_no_file is False."
            raise RuntimeError(error_msg)

        # We have a file to read, so let's try to read it
        try:  # noqa: PLR1702
            # Read and parse the JSON file
            with file_path.open("r", encoding="utf-8") as json_file:
                device_info = json.load(json_file)

            device_index = device["Index"]

            # HERE - change to included keys only

            # Update alloed device attributes
            device_included_keys = {"MACAddress", "Uptime", "RestartRequired"}
            for key, value in device_info.items():
                if key in device_included_keys and key in device:
                    device[key] = value

            # Update inputs
            if "Inputs" in device_info and device["Inputs"] > 0:
                for imported_input in device_info["Inputs"]:
                    # Find matching input by ComponentIndex
                    for device_input in self.inputs:
                        if (device_input["DeviceIndex"] == device_index and
                            device_input["ComponentIndex"] == imported_input.get("ComponentIndex")):
                            # Update just the State
                            device_input["State"] = imported_input.get("State", device_input["State"])

            # Update outputs
            if "Outputs" in device_info and device["Outputs"] > 0:
                for imported_output in device_info["Outputs"]:
                    # Find matching output by ComponentIndex
                    for device_output in self.outputs:
                        if (device_output["DeviceIndex"] == device_index and
                            device_output["ComponentIndex"] == imported_output.get("ComponentIndex")):
                            # Update just the State and Temperature if available
                            device_output["State"] = imported_output.get("State", device_output["State"])
                            if device["TemperatureMonitoring"]:
                                device_output["Temperature"] = imported_output.get("Temperature", device_output.get("Temperature"))

            # Update meters
            if "Meters" in device_info and device["Meters"] > 0:
                for imported_meter in device_info["Meters"]:
                    # Find matching meter by ComponentIndex
                    for device_meter in self.meters:
                        if (device_meter["DeviceIndex"] == device_index and
                            device_meter["ComponentIndex"] == imported_meter.get("ComponentIndex")):
                            # Update the meter reading values
                            for key, value in imported_meter.items():
                                if key in {"Power", "Voltage", "Current", "PowerFactor", "Energy"}:
                                    device_meter[key] = value
                            break

            # Update the device's total power and energy readings
            self._calculate_device_totals(device)

        except OSError as e:
            error_msg = f"Error reading JSON file {file_path}: {e}"
            self.logger.log_message(error_msg, "error")
            raise RuntimeError(error_msg) from e
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in file {file_path}: {e}"
            self.logger.log_message(error_msg, "error")
            raise RuntimeError(error_msg) from e
        except KeyError as e:
            error_msg = f"Missing expected key in JSON file {file_path}: {e}"
            self.logger.log_message(error_msg, "error")
            raise RuntimeError(error_msg) from e
        except RuntimeError as e:
            self.logger.log_message(f"Error importing device information from {file_path}: {e}", "error")
            raise RuntimeError(e) from e
        else:
            self._log_debug_message(f"Device simulation information imported from {file_path} for device {device['Label']}")
            return True
