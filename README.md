

# Home Assistant Component - Philips Dynalite

> Bridging the RS485 world of Philips Dynalite with the world of Home Assistant

Communicates with Philips Dynalite systems via an IP to RS485 controller.

This is a component for use with [Home Assistant](https://home-assistant.io/components/).

## Manual Installation
Until somebody wants to integrate this into Home Assistant - you will need to download or clone this repo and place the `dynalite` folder in your `custom_components` folder. Configuration is all via Home Assistant's config files - so please don't try and edit the contents of the component itself.

## Configuration
This is a messy one to configure because getting information out of Dynalite is near on impossible. You must know the configuration and topology of your network to be able to integrate with it - this isn't a "*plug and play*" scenario.

### Communication
The host and port of the RS485 to IP gateway is defined at the root of the sensor config, along with the MQTT discovery topic and device topic.
```yaml
dynalite:
  bridges:
    - host: 10.10.10.10     # IP Address of IP to 485 Gateway
      port: 12345           # Port for gateway typically 12345
      autodiscover: true    # When new presets or channels are activated on the network, add them dynamically
      polltimer: 1          # When there is a command with a fade (e.g. raise blinds), poll interval to find current status until it settles
      areacreate: create    # Automatically assign Home Assistant areas. Can be either 'create', which creates the areas on the fly, 'assign', which assigns devices to areas if they already exist, and 'manual' which ignores the areas
      log_level: DEBUG      # Turn this off when you have things working
```

### Areas
Areas are define under the `area` tag. Dynalite areas are numbered 1 through 255, you only need to define the areas you are using. At the very least every area needs a `name`.

Area's can have a `nodefault` tag (no default) which prevents them inheriting the default presets defined later.

Area's can have a `areaoverride` tag which means that the area should be under a different Home Assistant area. By default it goes to the same name as the area.

Area's can have `preset`'s defined that either augment or replace the default presets.

Area's can have `channels`'s defined, usually for individual lights or devices

Area's can have a `fade` time defined in seconds that will be used as a default fade time for preset changes in that area.

To use the dynalite component you will need to add the following to your
configuration.yaml file.
```yaml
dynalite:
  bridges:
    - host: 10.10.10.10
      port: 12345
      autodiscover: true
      polltimer: 1
      areacreate: create
      area:
        '9':
          name: Office
          channel:
            '1': 
              name: Center
            '2': 
              name: East
            '3': 
              name: West
        '10':
          name: Cinema
          channel:
            '1':
              type: switch
            '3':
        '108':
          name: Blind
          nodefault: true
          areaoverride: Office
          channel:
            '2':
              name: Blind
              type: cover
              factor: 0.73
              tilt: 0.02
      preset:
        '1':
          name: 'On'
          fade: 0
        '4':
          name: 'Off'
          fade: 0
      default:
        fade: 0

```

### Presets
Presets are optionally defined under `area`'s (as above) and are required to be defined in the root of the config under `preset`.

Preset's that you wish to call must be defined with at least a name.

Preset's may optionally also be defined with a `fade` time in seconds.
```yaml
      preset:
        '1':
          name: 'On'
          fade: 2
        '2':
          name: 70%
          fade: 2
        '3':
          name: 30%
          fade: 2
        '4':
          name: 'Off'
          fade: 2
        '9':
          name: Special Scene
          fade: 8
```

### Defaults
All default settings (which can be overridden per above) are defined here.

The default fade time is configured via the `fade` tag in seconds.
```yaml
      default:
        fade: 2
```

### Channels
Channels are optionally defined under `area`'s (as above) and are required to be defined in the root of the config under `channel`.

Channels that do not have a name will receive a name "AREANAM Channel X"

Channels can have an optional argument `type` which can be 'light', 'switch', or 'cover', creating the corresponding entity in Home Assistant. If not defined, 'light' is assumed

Channels of type 'cover' are ones where setting them to max level opens the cover and min level closes it. some covers (like mine) only need a portion of it, so if they are at 0 and go up to 0.75, they will be fully raised and stopped. This can be configures with the optional `factor` parameter

Some channels of type 'cover' also tilt and open the tilt when opening, and close it when closing, so it also has the optional `tilt` parameter which ssays how much of the full open/close is needed for just the tilt to adjust

## Special Thanks

* **Troy Kelly** - *Initial work* - [troykelly](https://github.com/troykelly)

Troy was responsible for the Dynalite python library and for a component that served as a base for this component. While refactored, most of this code comes from his repositories. Amazing work by him.
