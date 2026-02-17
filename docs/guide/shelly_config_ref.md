
```yaml
# This is an example configuration file for the Spello Consulting utility library

# Just an example section to show how to set up a section
AmberAPI:
  APIKey: This is not the real API key
  BaseUrl: https://api.amber.com.au/v1
  Timeout: 15

# Settings for oen or more Shelly smart switches. See documentation for more details.
ShellyDevices:
  AllowDebugLogging: True
  ResponseTimeout: 5
  RetryCount: 1
  RetryDelay: 2
  PingAllowed: True
  SimulationFileFolder: simulation_files
  # Enable or disable the webhook listener
  WebhooksEnabled: True
  # IP to listen for webhooks on. This should be the IP address of the machine running the app. Defaults to 0.0.0.0
  WebhookHost: 192.168.86.32
  # Port to listen for webhooks on. Defaults to 8787.
  WebhookPort: 8787
  # The URI path that webhooks will post to.
  WebhookPath: /shelly/webhook  
  # The webhooks to install by default
  DefaultWebhooks:
    Inputs:
      - input.toggle_on
      - input.toggle_off
      - input.button_push
    Outputs:
      - switch.on
      - switch.off
  Devices:
    - Name: Downstairs Lights
      Model: Shelly2PMG3
      Hostname: 192.168.1.23
      ID: 100
      Inputs:
        - ID: 101
          Name: "Living Room Switch"
          Webhooks: True
        - ID: 102
          Name: "Kitchen Switch"
          Webhooks: True
      Outputs:
        - ID: 111
          Name: "Living Room Relay"
        - ID: 112
          Name: "Kitchen Relay"
      TempProbes:
        - Name: "Outside Temp"
        - Name: "Inside Temp"
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


Files:
  # Name of the log file. Set to blak of None to disable logging
  LogfileName: logfile.log
  # How many lines of log file to keep. Set to 0 to disable log file truncation. Defaults to 10,000 if not specified 
  LogfileMaxLines: 500
  # How much information do we write to the log file. One of: none; error; warning; summary; detailed; debug, all. Defaults to detailed if not specified.
  LogfileVerbosity: all
  # How much information do we write to the console. One of: error; warning; summary; detailed; debug, all. Defaults to summary if not specified.
  ConsoleVerbosity: detailed

# Enter your settings here if you want to be emailed when there's a critical error 
Email:
  EnableEmail: True
  SendEmailsTo: 
  SMTPServer: smtp.gmail.com
  SMTPPort: 587
  SMTPUsername: 
  SMTPPassword: 
  SubjectPrefix: 
```

The entries are used as follows:

| Parameter | Description | 
|:--|:--|
| ResponseTimeout | How long to wait (in seconds) before timeing out when making an API call or ping. | 
| RetryCount | How many retries to make if an API call times out. | 
| RetryDelay | How long to wait (in seconds) between retry attempts. | 
| PingAllowed | Set to False if ICMP isn't suppported by the route to your devices. |
| SimulationFileFolder | The folder to save JSON simulation files in. | 
| WebhooksEnabled | Enable or disable the webhook listener |
| WebhookHost | IP to listen for webhooks on. This should be the IP address of the machine running the app. Defaults to 0.0.0.0. |
| WebhookPort | Port to listen for webhooks on. Defaults to 8787. |
| WebhookPath | The URI path that webhooks will post to. |
| DefaultWebhooks | The webhooks to install by default. See the example above for format. Look at the SupportedWebhooks key of an initialised Shelly device to see which webhook events your device supports. Use the  get_device() call to get a device object.  |
| Devices | A list of dicts, each on defining a Shelly device. - see below |

The Devices key in the configuration block supports the following keys :

| Parameter | Description | 
|:--|:--|
| Name | Your name for this device  |
| Model | The model Shelly ID for this device. See the [Shelly Models List](shelly_models_list.md) for more. |
| Hostname | The network IP address or hostname for this device. |
| ID | Your numeric ID for this device. |
| Simulate | Set this to True if you don't have access to the device but still want to test your code. When True, this device will be in 'simulation' mode. Rather than make API calls to the device, the state will be written to and read from a local json file (with the same name as your Name entry). You can modify some of the values in this file to test your code. |
| ExpectOffline | If set to True, we can expect this device to be offline at times. No warnings will be issued when this happens |
| Inputs | A list of dicts defining the inputs (if any) for this device. This section is optional but if defined, the number of entries must match the number of inputs supported by this model. For each input, define a Name and/or an ID. <br><br>Optionally, add a **Webhooks**: True entry here to install the default webhooks on this input. |
| Outputs | A list of dicts defining the outputs (if any) for this device. This section is optional but if defined, the number of entries must match the number of outputs supported by this model. For each output, define a Name and/or an ID. <br><br>Optionally, add a **Webhooks**: True entry here to install the default webhooks on this input. |
| Meters | A list of dicts defining the meters (if any) for this device. Note that depending on the devices, the actual meters might be part of the output or seperate energy meters (EM1 API calls). Either way, in this class meters are reported seperately from outputs. This section is optional but if defined, the number of entries must match the number of meters supported by this model. For each meter, define a Name and/or an ID.<br><br>  Optionally, use the **MockRate** key to set a Watts / second metering rate for this meter when the device is in Simulation mode. |
| TempProbes | A list of dicts defining the temperature probes connected to a Shelly Add-on that's plugged into this device. For each one you must define a Name key that matches the name given to the probe in the app (see below).<br><br>  Optionally, use the **RequiresOutput** key to specify the name of an output device that constrains this temp probe. If set, the temperature reading will only be updated when this output is on.  |

Notes:

- Either a Device Name or a Device ID must be supplied.
