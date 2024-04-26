#/bin/sh

mosquitto -d -c .devcontainer/mosquitto.conf
pip install -e local-console/
