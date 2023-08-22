#/bin/sh

mosquitto -d -c .devcontainer/mosquitto.conf
pip install -e wedge-cli/
