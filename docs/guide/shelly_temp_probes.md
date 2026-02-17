If you have a [Shelly Add-on](https://shelly-api-docs.shelly.cloud/gen2/Addons/ShellySensorAddon) installed on your Shelly switch, then you can connect up to 5 ds18b20 probes to the add-on. You must setup the probe(s) as follows before adding the probe's name to the ShellyDevices:Device:TempProbes section of your config file:

Once you have connected the Shelly Add-on to your Shelly smart switch and connected your DS18B20 temperature probes to the add on, you need to configure the probes in the mobile app:

1. Go to the Shelly device you have installed the Add-on to and configure the add-on
	- Click Add-on peripherals section
	- Change to Sensor Addon and then reboot if prompted
2. After reboot, go back to same tab and click Add Add-on Peripheral
	- Select Temperature (DS18B20)
	- Select a probe listed from the automatic scan and click Add Peripheral
	- Reboot when prompted
3. After reboot, go back to same tab and click the settings gear icon next to the newly added probe
	- Give the probe a name (important) - for example "Roof Temp"
	- Optionally enable the 'extract peripheral as device' option (if you want it to appear as a seperate device on your dashboard
4. Repeat steps 2 and 3 for any other connected probes

Now add these probe(s) to ShellyDevices:Device:TempProbes section of your config file, being sure to use exactly the same names as you used in the Shelly app.

```yaml
ShellyDevices:
  ...
  Devices:
    - Name: Downstairs Lights
      Model: Shelly2PMG3
      Hostname: 192.168.1.23
      ...
      TempProbes:
        - Name: "Roof Temp"
```
