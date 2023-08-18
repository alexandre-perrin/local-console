# Wedge CLI

Command line experience for *Wedge Agent*.

This tool simplifies the development of applications in a local environment by providing commands to build and interact with the agent to deploy and get the status.

## Getting Started

### Prerequisites

Before you begin, ensure that you have the following prerequisites in place:

* GNU make
* wasi-sdk:
```sh
curl -sL https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-20/wasi-sdk-20.0-linux.tar.gz | \
tar zxvf - -C /tmp && \
sudo mv /tmp/wasi-sdk-20.0 /opt/wasi-sdk
```
* mosquitto, with mosquitto.service running with default configuration
* Python 3.10 (or higher) and pip

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

Include `evp_agent` in `PATH` and run,

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
{'systemInfo': {'os': 'Linux', 'arch': 'x86_64', 'evp_agent': 'v1.20.0', 'protocolVersion': 'EVP2-TB'}, 'state/$agent/report-status-interval-min': 3, 'state/$agent/report-status-interval-max': 3, 'deploymentStatus': {'instances': {'sink_instance': {'status': 'ok', 'moduleId': 'sink'}, 'source_instance': {'status': 'ok', 'moduleId': 'source'}}, 'modules': {'source': {'status': 'ok'}, 'sink': {'status': 'ok'}}, 'deploymentId': 'bf031e17-6a26-475e-95d0-dede8e798cf8', 'reconcileStatus': 'ok'}}
```

#### Telemetry
If you're interested in telemetry data, you can retrieve it using the following command:
```sh
wedge-cli get telemetry
```
Example below:
```
{'sink_instance/my-topic': {'date': 'Fri Aug 18 08:56:44 2023', 'my-key': 'my-value'}}
```
