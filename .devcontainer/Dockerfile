FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
        build-essential make curl python3 python3-pip git cmake software-properties-common wget

# mosquitto
RUN add-apt-repository ppa:mosquitto-dev/mosquitto-ppa -y && apt install -y mosquitto
COPY .devcontainer/mosquitto.conf /app/mosquitto.conf

# wasi-sdk
RUN curl -sL https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-20/wasi-sdk-20.0-linux.tar.gz | tar zxvf - -C /tmp && \
    mv /tmp/wasi-sdk-20.0 /opt/wasi-sdk
RUN pip3 install kconfiglib
ENV PATH=~/.local/bin:$PATH

# wedge-agent
ARG WEDGE_AGENT_SAS_URL="https://cedata.blob.core.windows.net/main/wedge-agent_1.19.0_amd64.deb?sp=r&st=2023-08-22T07:14:58Z&se=2023-10-01T15:14:58Z&spr=https&sv=2022-11-02&sr=b&sig=9NFWjMOD0ujCphPeTwt6hj2q56f9FO155FDVEPM9hEA%3D"
RUN wget ${WEDGE_AGENT_SAS_URL} -k -O wedge-agent_1.19.0_amd64.deb
RUN apt install -y ./wedge-agent_1.19.0_amd64.deb
RUN cp -f /usr/bin/wedge_agent /usr/bin/evp_agent

# wedge-cli
COPY wedge-cli /app/wedge-cli
COPY samples /app/samples
WORKDIR /app
RUN pip install -e wedge-cli/
