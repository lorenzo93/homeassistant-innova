# Homeassistant Innova Fancoil Modbus integration

Homeassistant integration for the Innova Fancoils.
Beware that Innova sells its fancoils to other brands, the integration should still work.

Modbus official documentation available [here](https://www.innovaenergie.com/site/assets/files/2792/n273025c_kit_bridge_modbus_rtu_rev_01_en.pdf).

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

## Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `integration_blueprint`.
1. Download _all_ the files from the `custom_components/integration_blueprint/` directory (folder) in this repository.
1. Place the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Integration blueprint"

## Configuration is done in the configuration.yaml file

1. Configure the modbus integration with the correct data.
1. Add a climate device. In the configuration are shown all the possible parameters

```jaml
modbus:
  - name: modbus_hub
    type: tcp
    host: x.y.z.k

climate:
  - platform: modbus-innova
    name: Studio Fancoil
    slave: 19
    max_temp: 40
    min_temp: 5
```

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)