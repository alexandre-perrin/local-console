# syntax=docker/dockerfile:1

FROM busybox:latest as base

ARG FRP_VERSION=0.52.3
ARG BUILDARCH=amd64
ARG BUILDOS=linux

ARG FRP_HOST
ARG FRP_PORT
ARG FRP_TOKEN

RUN wget -O frp.tar.gz https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}/frp_${FRP_VERSION}_${BUILDOS}_${BUILDARCH}.tar.gz \
&& tar -xzf frp.tar.gz && mv /frp_${FRP_VERSION}_${BUILDOS}_${BUILDARCH} /frp

COPY frpc-mq.toml frpc.toml

RUN sed -i "s/FRP_HOST/${FRP_HOST}/g" frpc.toml && \
    sed -i "s/1000/${FRP_PORT}/g" frpc.toml && \
    sed -i "s/FRP_TOKEN/${FRP_TOKEN}/g" frpc.toml

FROM scratch

COPY --from=base /frp/frpc /frpc
COPY --from=base /frpc.toml /frpc.toml

CMD ["/frpc", "-c", "/frpc.toml"]
