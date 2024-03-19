# WEdge CLI

Command line experience for *WEdge Agent*.

This tool simplifies the development of applications in a local environment by providing commands to build and interact with the agent to deploy and get the status.

## Getting Started

### Prerequisites

#### 0. Language support

Make sure your system has installed:

* GNU make
* Python 3.9 (or higher)
* pip

#### 1. WEdge Agent

In order to build the agent, first clone the following repository

```sh
git clone git@github.com:midokura/evp-device-agent.git
```
and update the wedge agent submodule in the repo.

```sh
git submodule update --init
```
Follow the instructions in `wedge-agent/BUILD.md` to build the WEdge agent. Once
you have successfully built the agent, the `build` folder will be created.

Now, add the agent to the shell `$PATH`:

```sh
export PATH=/path/to/evp-device-agent/build/:$PATH
```

> [!WARNING]
> Use agent version 1.21.0 or higher.

Depending on what WEdge Agent version you mean to manage, the next prerequisites to put in place have version constraints as summarized below:

| Agent version | wasi-sdk version | wamrc version |
| ------------- | ---------------- | ------------- |
| older versions | Unsupported |
| 1.21 - 1.22 | 19 | 1.1.2 |
| 1.23 - 1.24 | 19 | 1.2.2 |
| 1.25+ | 20 | 1.3.0 |

We denote the versions required for wasi-sdk and wamrc as `$WASI_SDK_VER` and `$WAMRC_VER`, respectively.

#### 2. wasi-sdk

Download the software distribution and place it in a standard location:

```sh
curl -sL https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-$WASI_SDK_VER/wasi-sdk-$WASI_SDK_VER.0-linux.tar.gz | \
	tar zxvf - -C /tmp && \
	sudo mv /tmp/wasi-sdk-$WASI_SDK_VER.0 /opt/wasi-sdk
```
Optionally, you may avoid installing in a system-wide location such as `/opt`. If you do so, make sure that the environment variable `WASI_SDK_PATH` is exported in the shell where you will run the `wedge build` command.

#### 3. wamrc, the compiler from WAMR (WebAssembly Micro Runtime)

It is to be built with support for the Xtensa target, so that modules can be deployed on Type 3 cameras:

```sh
git clone https://github.com/bytecodealliance/wasm-micro-runtime.git wamr
git -C wamr checkout WAMR-$WAMRC_VER
cd wamr/wamr-compiler/
./build_llvm_xtensa.sh
mkdir build
(cd build; cmake .. && make)
sudo install -o root -g root -m 0755 ./build/wamrc /opt/wamrc/bin/wamrc
```

Make sure that `/opt/wamrc/bin` is present in your `$PATH`. If it is not, you may change the destination of `sudo install` (the last argument) to be somewhere already included in your `$PATH`.

#### 4. Mosquitto

In order to provide a local MQTT broker, we use `mosquitto`. Install [the software](https://mosquitto.org/download/). After installation, you can check it by using

```sh
mosquitto -version
```
By default, the mosquitto service will be up and running in the 1883 port. You can check the status by using:

```sh
systemctl status mosquitto.service
```
In case you want to initiate another mosquitto instance in another port you can run the following command:

```sh
mosquitto -c mosquitto.conf
```
And specify the port that you want to use with the parameter `listener` in `mosquitto.conf`.

> [!TIP]
> If you configure the broker to listen on a port `XXXX` other than the default 1883, you can specify it in the WEdge CLI config by doing `wedge config set mqtt port XXXX`

### Installation

```sh
pip install wedge-cli/
```

## Usage

For a comprehensive list of commands and their usage, check:

```sh
wedge-cli -h
```

### Example: Create an application and deploy

In this section, we explain how to deploy the sample application from [source-sink](./samples/source-sink)

1. Execute agent

```sh
wedge-cli start
```

2. Build an application

```sh
wedge-cli build
```

3. Deploy the application

```sh
wedge-cli --verbose deploy
```

it will show the following logs in between the topics recieved(this can be avoided by removing the `--verbose` option)
```
DEBUG: GET /bin/sink.wasm HTTP/1.1 200 -
DEBUG: GET /bin/source.wasm HTTP/1.1 200 -
```

and upon completion it will show
```
INFO: Deployment complete
```

The application will be deployed. Note that the final module identifiers to be used for the deployment, will be composed by suffixing the original module identifiers with a portion of the hash of the module binary. This is done to make sure that the agent's caching of downloaded modules will not inadvertenly skip downloading a newer version of a module, without you needing to change the module identifier by hand. Regarding the module instances, their identifiers remain unchanged, since there is no caching mechanism to beware.

#### Deployment status

To retrieve the deployment status, use the following command:
```sh
wedge-cli get deployment
```
This command will display information similar to:
```
{
   "systemInfo":{
      "os":"Linux",
      "arch":"x86_64",
      "evp_agent":"v1.20.0",
      "protocolVersion":"EVP2-TB"
   },
   "state/$agent/report-status-interval-min":3,
   "state/$agent/report-status-interval-max":3,
   "deploymentStatus":{
      "instances":{
         "sink_instance":{
            "status":"ok",
            "moduleId":"sink"
         },
         "source_instance":{
            "status":"ok",
            "moduleId":"source"
         }
      },
      "modules":{
         "source":{
            "status":"ok"
         },
         "sink":{
            "status":"ok"
         }
      },
      "deploymentId":"bf031e17-6a26-475e-95d0-dede8e798cf8",
      "reconcileStatus":"ok"
   }
}
```

#### Telemetry

If you're interested in telemetry data, you can retrieve it using the following command:
```sh
wedge-cli get telemetry
```
Example below:
```
{
   "sink_instance/my-topic":{
      "date":"Fri Aug 18 08:56:44 2023",
      "my-key":"my-value"
   }
}
```

#### Configuration

If you have to configure parameters for the Wedge agent, the MQTT broker or the webserver used by the agent to
download the modules you can use

```sh
wedge-cli config set <section> <option> <value>
```
and you can consult the values by using

```sh
wedge-cli config get <section> <option>
```

##### Optional parameters

Some parameters are nullable, such as `device_id` in the `mqtt` section. If you need to set such a parameter back to null (i.e. clear the parameter), you may use the `unset` action as follows:

```sh
wedge-cli config unset <section> <option>
```

Nullable parameters will show up in the output of `config get` as assigned with `= None`

### Using TLS for MQTT

The CLI supports connecting to the broker (and issuing a client certificate for the device) when the paths to a CA certificate and its private key are registered, by doing:

```sh
wedge-cli config set tls ca_certificate path/to/ca/certificate_file
wedge-cli config set tls ca_key path/to/ca/private_key_file
```

> [!TIP]
> Don't forget to also update the `mqtt port` setting, as the default `1883` is for unsecured MQTT connections, whereas it is customary to use `8883` for TLS connections.

> [!WARNING]
> If you will be running the MQTT broker in the same machine as the CLI and agent are running, then you will need to install [nss_wrapper](https://cwrap.org/nss_wrapper.html), so that the agent can verify the local server certificate when doing the TLS handshake.

### GUI mode

The CLI includes a graphical interface that you may start with

```sh
wedge-cli gui
```

On start up, it spawns a MQTT broker instance listening on the configured port. Then a camera can connect to this broker, so that the GUI can provide access to camera actions such as image streaming.

#### Additional Dependencies

The GUI supports running on Linux and Windows.
- For Windows, an installer will be provided separately, which shall take care of dependencies.
- For Linux:
   - The `xclip` clipboard client.
   - The `mosquitto` MQTT broker.

### Configuring the camera via QR code

The CLI can generate a QR code for camera onboarding, so that the camera can connect to its broker:

```sh
wedge-cli qr
```

By default, it will use the settings of the CLI. If the MQTT host is set to localhost, it will produce the QR code with the IP address of the externally-accessible interface to the local machine. For other settings, try the `--help` flag.

## App samples

You can find examples of apps in the [samples](./samples) folder and the documentation for each sample app in the [docs](./docs) folder.