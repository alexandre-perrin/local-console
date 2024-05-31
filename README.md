# Local Console

This program provides a CLI and a GUI which simplify offline usage of IMX500-equipped smart cameras, and development of applications to deploy on them.

## Getting Started

### Prerequisites

#### 0. System support

Make sure your system has installed:

* Python 3.10 (or higher)
* pip

#### 1. Mosquitto

In order to provide a local MQTT broker, we use `mosquitto`. Install [the software](https://mosquitto.org/download/). After installation, you can check it by using

```sh
mosquitto -h
```
By default, the mosquitto service will be up and running in the 1883 port. You can check the status by using:

```sh
systemctl status mosquitto.service
```
Make sure that its installation did not enable a running instance, by doing:

```sh
sudo systemctl disable mosquitto.service
sudo systemctl stop mosquitto.service
```

This action is only necessary once (i.e. after installing the software).

> [!TIP]
> If you configure the broker to listen on a port `XXXX` other than the default 1883, you can specify it in the CLI config by doing `local-console config set mqtt port XXXX`

### Installation

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e local-console/
```

## Usage

For a comprehensive list of commands and their usage, check:

```sh
local-console --help
```

Run Local Console,

```sh
local-console gui
```

On start up, it spawns a MQTT broker instance listening on the configured port. Then a camera can connect to this broker, so that the GUI can provide access to camera actions such as image streaming.

#### Additional Dependencies

The GUI supports running on Linux and Windows.
- For Windows, an installer will be provided separately, which shall take care of dependencies.
- For Linux:
   - The `xclip` clipboard client.
