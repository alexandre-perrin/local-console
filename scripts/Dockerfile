#
# This Dockerfile is for generating OSS license report.
#
FROM python:3.11.8-slim-bookworm

# Minimum dependencies for GUI
RUN apt-get update && apt-get install -y mosquitto

# required to download "kivymd"
RUN apt-get update && apt-get install -y git

COPY . .
RUN pip install wedge-cli/

# Clean up unnecessary packages
# * git is not required as it is not included in the artifacts that we release
RUN apt-get purge -y git
