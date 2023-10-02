# Source-Sink Example

This example demonstrates the basic usage of a sensing application with 2 modules that communicate.
It is conformed by 2 modules, the source and the sink. The source sends the date to the sink, and the sink reports
the date as a telemetry.

The deployment.json of ths application can be seen as an example to establish communication between 2 modules.

You can retrieve the telemetry data

```
wedge-cli get telemetry
```

and the report will look like this,

```
{'sink_instance/my-topic': {'date': 'Mon Oct  2 13:55:40 2023', 'my-key': 'my-value'}}
```


