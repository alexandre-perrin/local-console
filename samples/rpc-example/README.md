# RPC Example

This example demonstrates the use of Remote Procedure Calls (RPC) with wedge-cli.

1. Retrieve default telemetry data

```
wedge-cli get telemetry
```

The report will look like this,

```
{'node/my-topic': {'r': '0', 'g': '0', 'b': '0'}}
```

2. Modify the colour with RPC

```
wedge-cli rpc node my-method '{"rgb": "000F01"}'
```

3. Retrieve telemetry data

```
wedge-cli get telemetry
```

Now telemetry will report,

```
{'node/my-topic': {'r': '0', 'g': '15', 'b': '1'}}
```
