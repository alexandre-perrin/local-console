# Local Console

An offline tool to interact with IMX500-equipped smart cameras and develop applications for them. This software provides the following functionalities:

- Connection configuration
- Streaming control
- WASM Module deployment
- AI model deployment
- Camera firmware update

## Prerequisites

The Local Console requires the following dependencies to be installed on your system:

* Python 3.11 (or higher), pip
* [mosquitto](https://mosquitto.org/download)
* [flatc](https://github.com/google/flatbuffers/releases/tag/v24.3.25)

Make sure these programs are added to your system's `PATH` environment variable.

## Installation

The installation procedure depends on your machine. It is outlined for each supported OS below.

> [!TIP]
> Make sure your machine has a working Internet access, as all variants of the installation procedure will require downloading third-party dependencies.

### Windows

You should execute the `local-console-setup.exe` installer, as your regular (i.e. non-admin) user. In order for the installer to download the system dependencies, the installer will attempt to run a shell script as an Administrator, causing Windows' UAC to prompt for your permission to do so. Once the system dependencies are installed, another shell script will be executed as your user, which will actually install the Local Console in your user account.

### Linux

Currently there is no stand-alone installer as there is for Windows. Hence, after fulfilling [the prerequisites](#prerequisites), perform the following steps:

1. Install `xclip` (e.g. in Debian-based)
2. Create a python virtual environment:

```sh
$ python3.11 -m venv lcenv
$ . lcenv/bin/activate
(lcenv)$
```

3. Install the python wheel `local_console-*-py3-none-any.whl`:

```sh
(lcenv)$ pip install local_console-*-py3-none-any.whl
```

The Local Console has been installed. To use it, either run the `local-console` command with the `lcenv` virtualenv activated, or use the absolute path to the `local-console` binary located in the `bin` subdirectory at the location of the `lcenv` virtualenv.

### OSX

The procedure is pretty similar to [Linux](#linux), except for the `xclip` requirement, which is unnecessary for this platform.

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
local-console config set <section> <value>
```

and you can query the current values by using

```sh
local-console config get <section>
```

To modify or query device parameters, use the option `-d/--device`.

#### Optional parameters

Some parameters are nullable, such as `device_id` in the `mqtt` section. If you need to set such a parameter back to null (i.e. clear the parameter), you may use the `unset` action as follows:

```sh
local-console config unset <section>
```

Nullable parameters will show up in the output of `config get` as assigned with `= None`

### Configuring the camera via QR code via CLI

The CLI can generate a QR code for camera onboarding, so that the camera can connect to its broker:

```sh
local-console qr
```

By default, it will use the settings of the CLI. If the MQTT host is set to localhost, it will produce the QR code with the IP address of the externally-accessible interface to the local machine. For other settings, try the `--help` flag.
