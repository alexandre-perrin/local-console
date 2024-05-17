#!/bin/sh
# Copyright 2024 Sony Semiconductor Solutions Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

set -e

HERE=$(cd $(dirname $0); pwd -P)

mkdir -p ${HERE}/certificates

cd ${HERE}/certificates

# $1 - base file name
# $2 - subject common name
# $3 - subject alternative name
make_cert () {
    openssl genrsa -out ${1}.key 2048
    openssl req -out ${1}.csr -key ${1}.key -new \
        -subj "/C=ES/ST=BCN/L=Barcelona/O=Midokura/OU=Wedge/CN=${2}/" \
        -addext "subjectAltName = DNS:${3}"

    TMPFILE=$(mktemp)
    printf "subjectAltName = DNS:${3}" > ${TMPFILE}

    openssl x509 -req -in ${1}.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out ${1}.crt -days 365 \
        -extfile ${TMPFILE} \
        -subj "/C=ES/ST=BCN/L=Barcelona/O=Midokura/OU=Wedge/CN=${2}/" \

    rm ${TMPFILE}
}

rm -rf ${HERE}/certificates/*
# CA
openssl req -new -x509 -days 365 -extensions v3_ca -keyout ca.key -out ca.crt -nodes \
    -subj "/C=ES/ST=BCN/L=Barcelona/O=Midokura/OU=Wedge/CN=Wedge CA/"

# service certificates
make_cert mqtt-server "Wedge MQTT Server" mqtt.local

# client certificates
make_cert client "Wedge Agent" client

# pytest certificates
make_cert pytest "Pytest Client" pytest
