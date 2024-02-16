# Based on https://github.com/bytebeamio/rumqtt/blob/main/rumqttd/rumqttd.toml
id = 0

[router]
id = 0
max_connections = 10010
max_outgoing_packet_count = 200
max_segment_size = 104857600
max_segment_count = 10

# Configuration of server and connections that it accepts
[v4.1]
name = "v4-1"
listen = "0.0.0.0:${mqtt_port}"
next_connection_delay_ms = 1
    [v4.1.connections]
    connection_timeout_ms = 60000
    max_payload_size = 20480
    max_inflight_count = 100
    dynamic_filters = false
