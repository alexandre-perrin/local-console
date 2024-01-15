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


```sh
```



```sh
```

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

it will show a message similar to
```
INFO: Downloaded module bin/source.wasm
INFO: Downloaded module bin/sink.wasm
```

The application will be deployed.

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
