# syntax=docker/dockerfile:1

FROM eclipse-mosquitto:2.0.18

COPY mosquitto.conf /mosquitto/config/mosquitto.conf

COPY certificates ./certificates

RUN apk upgrade --update-cache --available && \
    apk add openssl && \
    rm -rf /var/cache/apk/*

EXPOSE 8883

RUN chmod -R a+r /certificates/.
