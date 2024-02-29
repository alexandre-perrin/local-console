#
# This Dockerfile is for generating OSS license report.
#
FROM python:3.9.17-slim-bookworm

RUN apt-get update && apt-get install -y \
        make cmake git curl wget software-properties-common

# mosquitto
RUN apt-get update && apt-get install -y mosquitto

# wedge-cli
COPY . .
RUN pip install wedge-cli/
