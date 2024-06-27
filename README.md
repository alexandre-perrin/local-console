# Local Console

An offline tool to interact with IMX500-equipped smart cameras and develop applications for them.

## Open source and proprietary source split

The Local Console code has been modularized into two bases: a public one, (to-be) released as Open Source Software (OSS) and a proprietary one. The design of this split is as follows:
- The OSS code lives at [SonySemiconductorSolutions/local-console](https://github.com/SonySemiconductorSolutions/local-console). It provides the base functional set, such as connection configuration, module deployment, sensor network upload and streaming control. This is distributed in binary form, as a Python wheel and a Windows installer.
- The proprietary code lives in this repository. It is a set of plugins on top of the OSS code, which adds functionality that depends on proprietary components such as the [Wedge Agent SDK](https://github.com/midokura/wedge-agent/tree/main/include/evp). This plugin set is packaged as a Python wheel, to be installed on the same virtual environment created for an installation of the base OSS code.

## Installation

You start off an installation of the OSS local-console distribution. Please refer to its [instructions for installations](https://github.com/SonySemiconductorSolutions/local-console?tab=readme-ov-file#installation) before continuing here. Then, locate the installation path as detailed below:

### Path to your local-console virtual environment

#### On Windows

By default, the Python interpreter (`python.exe`) of the virtual environment of the local-console installation is located at `%LOCALAPPDATA%\Programs\LocalConsole\virtualenv\Scripts`. When in doubt, read the destination path of the Local Console GUI shortcut on the Desktop.

#### On Linux and OSX

There is no default installation path for Linux, so you will need to recall the location of the virtual environment you created when you installed the OSS local-console.

### Installing at your path


Then, install Local Console with the following commands:

```sh
$PATH_TO_YOUR_PYTHON_INTERPRETER -m pip install -e local-console/
```

#### Mosquitto

By default, the mosquitto service runs on port 1883. You can check its status with:

```sh
systemctl status mosquitto.service
```

Make sure that its installation did not enable a running instance, by doing:

```sh
sudo systemctl disable mosquitto.service
sudo systemctl stop mosquitto.service
```

This action is only necessary once after installing the software.

## Usage

To display help information, use:

```sh
local-console --help
```

### Get Started


#### GUI mode

To run the Local Console GUI, use:

```sh
local-console gui
```

On start up, it spawns a MQTT broker instance listening on the configured port. Then a camera can connect to this broker, so that the GUI can provide access to camera actions such as image streaming.

### Persistent configuration parameters via CLI

For configuring connection parameters for the devices (or the simulated agents), you can use:

```sh
local-console config set <section> <option> <value>
```
and you can query the current values by using

```sh
local-console config get [<section> <option>]
```

#### Optional parameters

Some parameters are nullable, such as `device_id` in the `mqtt` section. If you need to set such a parameter back to null (i.e. clear the parameter), you may use the `unset` action as follows:

```sh
local-console config unset <section> <option>
```

Nullable parameters will show up in the output of `config get` as assigned with `= None`

### Configuring the camera via QR code via CLI

The CLI can generate a QR code for camera onboarding, so that the camera can connect to its broker:

```sh
local-console qr
```

By default, it will use the settings of the CLI. If the MQTT host is set to localhost, it will produce the QR code with the IP address of the externally-accessible interface to the local machine. For other settings, try the `--help` flag.

### Using TLS for MQTT

Local-console supports connecting to the broker (and issuing a client certificate for the device) when the paths to a CA certificate and its private key are registered, by doing:

```sh
local-console config set tls ca_certificate path/to/ca/certificate_file
local-console config set tls ca_key path/to/ca/private_key_file
```

> [!TIP]
> Don't forget to also update the `mqtt port` setting, as the default `1883` is for unsecured MQTT connections, whereas it is customary to use `8883` for TLS connections.
