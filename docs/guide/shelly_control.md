# Getting Started with ShellyControl

The [ShellyControl class](../reference/shelly_control.md) is designed to make it easy to integrate with Shelly smart switches. Specifically this library supports switches and energy meter as allows you to:

- Get the status of a device including temperature, Mac address, etc. 
- See if a device is online or not
- Read the current state of an input switch 
- Read the current state of an output relay
- Read an energy meter including power, energy, voltage, current and power factor (where available)
- Change the state of an output relay (i.e. turn on or off)

This library supports many device types (30 at the last count) including older models no longer sold by the vendors. 

This library also isolates you from having to deal with the idiosyncrasies of the Shelly APIs. The vendor completely changed the API for generation 2 devices and later, and even with the new API it’s rather complex deal with the different model types and the API calls they support. This library includes a _shelly_models.json_ file that defines the capabilities of each model. Use the print_model_library() method to view this information.

## Initialisation

To initialise an instance of the ShellyControl class, you need to pass it:

1. A SCLogger object - use the [SCLogger](../reference/logging.md) class to get one of these.
2. A dict object containing the configuraton of the Shell devices that you want to manage. This information is normally stored in a YAML configuration file and can be read from that file using [SCConfigManager.get_shelly_settings()](../reference/configmanager.md)

Here's an example of a section of yaml file configuration for 3 Shelly devices

    ShellyDevices:
      ResponseTimeout: 5
      RetryCount: 1
      RetryDelay: 2
      PingAllowed: True
      Devices:
        - Name: Downstairs Lights
          Model: Shelly2PMG3
          Hostname: 192.168.1.23
          ID: 100
          Inputs:
            - ID: 101
              Name: "Living Room Switch"
            - ID: 102
              Name: "Kitchen Switch"
          Outputs:
            - ID: 111
              Name: "Living Room Relay"
            - ID: 112
              Name: "Kitchen Relay"
        - Name: Outside Lights
          Model: Shelly2PMG3
          Hostname: 192.168.1.25
          ID: 200
          Inputs:
            - ID: 201
              Name: "Patio Switch"
            - ID: 202
              Name: "Car Port Switch"
          Outputs:
            - ID: 211
              Name: "Patio Relay"
            - ID: 212
              Name: "Car Port Relay"
        - Name: Testing
          Model: ShellyPlus1PM
          Simulate: True
          Outputs:
            - Name: "Test Switch"
          Meters:
            - Name: "Test Meter"

The entries are used as follows:

| Parameter | Description | 
|:--|:--|
| ResponseTimeout | How long to wait (in seconds) before timeing out when making an API call or ping. | 
| RetryCount | How many retries to make if an API call times out. | 
| RetryDelay | How long to wait (in seconds) between retry attempts. | 
| PingAllowed | Set to False if ICMP isn't suppported by the route to your devices. |
| Devices | A list of dicts, each on defining a Shelly device. - see below |

The Devices key in the configuration block supports the following keys :

| Parameter | Description | 
|:--|:--|
| Name | Your name for this device  |
| Model | The model Shelly ID for this device. See the [Shelly Models List](shelly_models_list.md) for more. |
| Hostname | The network IP address or hostname for this device. |
| ID | Your numeric ID for this device. |
| Simulate | Set this to True if you don't have access to the device but still want to test your code. When True, this device will be in 'simulation' mode. Rather than make API calls to the device, the state will be written to and read from a local json file (with the same name as your Name entry). You can modify some of the values in this file to test your code. |
| Inputs | A list of dict defining the inputs (if any) for this device. This section is optional but if defined, the number of entries must match the number of inputs supported by this model. For each input, define a Name and/or an ID. |
| Outputs | A list of dict defining the outputs (if any) for this device. This section is optional but if defined, the number of entries must match the number of outputs supported by this model. For each output, define a Name and/or an ID. |
| Meters | A list of dict defining the meters (if any) for this device. Note that depending on the devices, the actual meters might be part of the output or seperate energy meters (EM1 API calls). Either way, in this class meters are reported seperately from outputs. This section is optional but if defined, the number of entries must match the number of meters supported by this model. For each meter, define a Name and/or an ID. |

Note:

- Either a Device Name or a Device ID must be supplied.

## Future Features 

Some of the things this library might support in the future:

- Support for Authentication
- Support for call backs so that your app can be notified when an input changes state
- Support for other types of Shelly device

## Sample code

```python

  {%
    include "../../examples/shelly_example.py"
  %}
```