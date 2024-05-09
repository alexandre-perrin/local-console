# syntax=docker/dockerfile:1

FROM busybox:latest as base

ARG FRP_VERSION=0.52.3
ARG BUILDARCH=amd64
ARG BUILDOS=linux

ARG FRP_HOST
ARG FRP_EXTERNAL_PORT
ARG INTERNAL_PORT
ARG FRP_TOKEN
ARG FRP_NAME_SUFFIX
ARG INTERNAL_HOST
ARG SERVICE_NAME

RUN wget -O frp.tar.gz https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}/frp_${FRP_VERSION}_${BUILDOS}_${BUILDARCH}.tar.gz \
&& tar -xzf frp.tar.gz && mv /frp_${FRP_VERSION}_${BUILDOS}_${BUILDARCH} /frp

COPY frpc-mq.toml frpc.toml

RUN sed -i "s/FRP_HOST/${FRP_HOST}/g" frpc.toml && \
    sed -i "s/FRP_EXTERNAL_PORT/${FRP_EXTERNAL_PORT}/g" frpc.toml && \
    sed -i "s/FRP_TOKEN/${FRP_TOKEN}/g" frpc.toml && \
    sed -i "s/FRP_NAME_SUFFIX/${FRP_NAME_SUFFIX}/g" frpc.toml && \
    sed -i "s/INTERNAL_PORT/${INTERNAL_PORT}/g" frpc.toml && \
    sed -i "s/INTERNAL_HOST/${INTERNAL_HOST}/g" frpc.toml && \
    sed -i "s/SERVICE_NAME/${SERVICE_NAME}/g" frpc.toml

FROM busybox:latest

COPY --from=base /frp/frpc /frpc
COPY --from=base /frpc.toml /frpc.toml
COPY retry.sh /retry.sh

CMD ["sh", "/retry.sh", "/frpc", "-c", "/frpc.toml"]
