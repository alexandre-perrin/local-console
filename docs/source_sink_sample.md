# Source-Sink Example

This example demonstrates the basic usage of a sensing application with 2 modules that communicate.
It is conformed by 2 modules, the source and the sink. The source sends the date to the sink, and the sink reports
the date as a telemetry.

The deployment.json of this application can be took as a reference to establish communication between 2 modules.

Make sure that you have the agent running and follow the next steps:

1. Build the application

Move to the [source-sink sample directory](../samples/source-sink) path and build the application by running

```sh
wedge-cli build
```

2. Deploy the application

Once the applicattion is built deploy it to the agent by running

```sh
wedge-cli --verbose deploy
```


3. Retrieve the telemetry data sent by the sink by using the following command

```sh
wedge-cli get telemetry
```

and the report will look like this,

```
{'sink_instance/my-topic': {'date': 'Mon Oct  2 13:55:40 2023', 'my-key': 'my-value'}}
```


