# ShellyControl Object Reference

This page provides a quick reference to the attributes of the main ShellyControl dictionary object types. 

## Devices

ShellyControl.devices is a list of all the Shelly smart switch devices being managed by this class. You can reference this attribute directly or use ShellyControl.get_device() to return a device dict, looking up by ID, name, etc. 

Each device has the following attrbutes

- **Index**: The index of the device in the devices list. Counts from 0.
- **Model**: The model tag, used to look up the device characteristics in the shelly_models.json file~
- **ClientName**: Client provided name for the device~
- **ID**: Client provided numeric ID for the device, or auto numbered (starting at 1) if not provided~
- **ObjectType**: Will always be 'device'
- **Simulate**: Whether to simulate the device or not, default is False~
- **SimulationFile**: The file to use for simulation. None if not in simulation mode.
- **ModelName**: The vendor's model name**
- **Label**: Combination of the ClientName and ID used in logging messages
- **URL**: URL to the vendor's product page**
- **Hostname**: The DNS hostname or IP address of the device~
- **Port**: The port number to use for communication with the device, default is 80~
- **Generation**: Numeric value representing which generation this device is.**
- **Protocol**: Which API protocol is used to communicate with the device: REST or RPC**
- **Inputs**: Number of switch inputs supported by the device, if any**
- **Outputs**: Number of relay outputs supported by the device, if any**
- **Meters**: Number of energy meters supported by the device, if any**
- **MetersSeperate**: Are the energy meters separate from the relay outputs?**
- **TemperatureMonitoring**: Is temperature monitoring supported by the device?**
- **Online**: Is the device online?^
- **MacAddress**: The MAC address of the device, if available.^
- **Temperature**: The current temperature of the device, if available.^
- **Uptime**: The uptime of the device in seconds, if available.^
- **RestartRequired**: Whether the device requires a restart to apply changes, if available.^
- **SupportedWebhooks**: If this device supports webhooks, this will list the event types supported.
- **InstalledWebhooks**: The list of webhooks currently installed on this device.
- **customkeylist**: A list of any custom key / value pairs that have been added to the device via the configuration file.

## Device Components

A component is a specific hardware component of a Shelly device. Three component types are supported:

- **Inputs**: An input usually wiring in from a physical light switch. Used to send a hardware signal to the Shelly device (e.g. light switch has been turned on)
- **Outputs**: A relay output from the Shelly device. This is how the Shelly controls things like lights, motors, etc.
- **Meters**: An energy meter that can measure the voltage, current and power draw on an output or a dedicated external eMeter clamps (depending on the model).

Different Shelly models have different numbers of inputs, outputs and meters and some may have only a subset of these features. The print_model_library() function will return a list of all supported Shelly devices and the number and type of components that each model supports. The Inputs, Outputs and Meters attributes of the device object (see above) provides a count of the number of components of each type supported by that particular device.

All components support the following core attrbutes:

- **DeviceIndex**: The Index of the parent device that this component is a part of.
- **DeviceID**: The ID of the parent device that this component is a part of.~
- **ComponentIndex**: The index of the component in the list of components of this type on this device. For example the second Input component on the third device in our list will have a ComponentIndex=1. 
- **ObjectType**: What type of component is this - one of input; output or meter.
- **ID**: Client provided numeric ID for the component, or auto numbered (starting at 1) if not provided. This is unique.~
- **Name**: Client provided name for the component~
- **Webhooks**: True if one or more webhooks have been set for this component.
- **customkeylist**: A list of any custom key / value pairs that have been added to the component via the configuration file.

### Input component

Input components will also have these attrbutes:

- **State**: Is the input currently on (True) or off (False).

### Output component

Output components will also have these attrbutes:

- **HasMeter**: Is there an energy meter associated with this output.
- **State**: Is the output currently on (True) or off (False).
- **Temperature**: Reported temperature reading for this output relay.

### Meter component

Meter components will also have these attrbutes:

- **OnOutput**: Is this meter part of an output relay (True) or a seperate eMeter (False)
- **Power**: Current power reading in watts.
- **Voltage**: Current voltage reading.
- **Current**: Current current reading.
- **PowerFactor**: The power factor reading.
- **Energy**: Total energy consumed in watt / hours. (When a device is an Simulation mode, you can add a MockRate key to the Meter's configuration section to set a Watts/second metering rate.)

Note, depending on the Shelly models, some of these attrbutes may be empty. For example, some earlier generation 1 models would report power but not voltage or current.

## Footnotes

**These attributes are retrieved from the _shelly_models.json_ file.
~These attributes are provided by the client in the configuration file.
^This attribute is set when checking the switch status.