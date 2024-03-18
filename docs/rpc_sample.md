# RPC Sample Application

This example demonstrates how to build, deploy and the sameple application that demonstates the usage of Remote Procedure Calls (RPC) with wedge-cli.
The application reports continuosly thprugh telemtry the three values of an RGB colour space. This values can be modified by sending an RPC with the RGB values in Hex format, as specified below.
Make sure that you have the agent running and follow the next steps:

1. Build the application

Move to the [rpc sample directory](../samples/rpc-example) path and build the application by running

```sh
wedge-cli build
```

2. Deploy the application

Once the applicattion is built deploy it to the agent by running

```sh
wedge-cli --verbose deploy
```


3. Retrieve default telemetry data by using the following command

```sh
wedge-cli get telemetry
```

The report will look like this,

```
{'node/my-topic': {'r': '0', 'g': '0', 'b': '0'}}
```

4. Modify the colour with RPC command

```sh
wedge-cli rpc node my-method '{"rgb": "000F01"}'
```

5. Retrieve telemetry data

```sh
wedge-cli get telemetry
```

Now the telemetry will reportthe previous RGB values sent,

```
{'node/my-topic': {'r': '0', 'g': '15', 'b': '1'}}
```
