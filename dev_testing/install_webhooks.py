def install_shelly_webhooks(controller: LightingController, logger: SCLogger, cfg: WebhookConfig) -> None:  # noqa: PLR0912, PLR0915
    """Install the input trigger webhooks for Shelly devices.

    Args:
        controller: The lighting controller instance.
        logger: The logger instance.
        cfg: The webhook configuration.

    Raises:
        TimeoutError: There's no response from the switch.
        RuntimeError: If the webhook installation fails.
    """
    if not cfg:
        logger.log_fatal_error("No webhook configuration provided when calling install_shelly_webhooks.")
        return

    # Look through each device in the controller
    for device in controller.shelly_control.devices:
        # Build a consolidated object of the device including its inputs
        device_info = controller.shelly_control.get_device_information(device)

        # Skip the device if it has no inputs
        if device.get("Inputs", 0) == 0:
            logger.log_message(f"Device {device.get('Name')} has no inputs, skipping webhook installation.", "debug")
            continue

        # Enumerate the device's inputs and see if we can find any of these in the switch_states list
        for device_input in device_info.get("Inputs", []):
            input_name = device_input.get("Name")
            if input_name not in controller.switch_states:
                logger.log_message(f"Input {input_name} on device {device.get('Name')} not associated with any switch_states, skipping webhook installation for this input.", "debug")
                continue


        # If we get this far, we have at least one input on this device mentioned in our configuration, so install the webhooks
        try:
            # First do a Webhook.ListSupported call and make sure our webhooks are supported
            payload = {"id": 0,
                       "method": "Webhook.ListSupported"}
            result, result_data = controller.shelly_control._rpc_request(device, payload)  # noqa: SLF001
            if not result:
                logger.log_message(f"Failed to list supported web hooks for device {device.get('Name')}: {result_data}", "error")
                continue

            # The result_data should contain our supported webhook types
            supported_types = result_data.get("types", {})
            if ("input.toggle_on" not in supported_types) or ("input.toggle_off" not in supported_types):
                logger.log_message(f"Device {device.get('Name')} does not support the webhook types input.toggle_on and input.toggle_off. Skipping", "error")
                continue

            # Clear all existing web hooks for this device
            payload = {"id": 0,
                    "method": "Webhook.DeleteAll"}
            result, result_data = controller.shelly_control._rpc_request(device, payload)  # noqa: SLF001
            if not result:
                logger.log_message(f"Failed to delete existing web hooks for device {device.get('Name')}: {result_data}", "error")
                continue

            # Loop through the named inputs for this device
            for device_input in device_info.get("Inputs", []):
                input_name = device_input.get("Name")
                input_component = controller.shelly_control.get_device_component("input", input_name)

                # Now install the toggle on web hook
                payload = {"id": 0,
                        "method": "Webhook.Create",
                        "params": {"cid": input_component.get("ComponentIndex"),
                                    "enable": True,
                                    "event": "input.toggle_on",
                                    "name": f"Toggle On: {input_component.get('ComponentIndex')}",
                                    "urls": [f"http://{cfg.host}:{cfg.port}{cfg.path}?component={input_component.get('ComponentIndex')}&state=on"]}}
                result, result_data = controller.shelly_control._rpc_request(device, payload)  # noqa: SLF001
                if result:
                    logger.log_message(f"Installed toggle_on webhook rev {result_data.get('rev')} for input {input_component.get('Name')}", "debug")
                else:
                    logger.log_message(f"Failed to create input on web hooks for input {input_component.get('Name')}: {result_data}", "error")
                    continue

                # Now install the toggle off web hook
                payload = {"id": 0,
                        "method": "Webhook.Create",
                        "params": {"cid": input_component.get("ComponentIndex"),
                                    "enable": True,
                                    "event": "input.toggle_off",
                                    "name": f"Toggle Off: {input_component.get('ComponentIndex')}",
                                    "urls": [f"http://{cfg.host}:{cfg.port}{cfg.path}?component={input_component.get('ComponentIndex')}&state=off"]}}
                result, result_data = controller.shelly_control._rpc_request(device, payload)  # noqa: SLF001
                if result:
                    logger.log_message(f"Installed toggle_off webhook rev {result_data.get('rev')} for input {input_component.get('Name')}", "debug")
                else:
                    logger.log_message(f"Failed to create input on web hooks for input {input_component.get('Name')}: {result_data}", "error")
                    continue

        except TimeoutError as e:
            logger.log_message(f"Timeout error installing web hooks for device {device.get('Name')}: {e}", "error")
            raise TimeoutError(e) from e
        except RuntimeError as e:
            logger.log_message(f"Error installing web hooks for device {device.get('Name')}: {e}", "error")
            raise RuntimeError(e) from e

