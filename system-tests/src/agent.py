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
import itertools
import logging
import subprocess
import tarfile
import time
from base64 import b64encode
from collections.abc import Callable
from pathlib import Path
from typing import Any
from typing import cast
from typing import Literal
from uuid import uuid4

from devispare import ApiClient
from devispare import Configuration
from devispare import Deployment
from devispare import JobInfo
from devispare import JobStatus
from devispare import ResponseStatus
from devispare.api import JobsApi
from littlefs import LittleFS
from pydantic import BaseModel
from src.interface import OnWireSchema

BASE_DIR = Path(__file__).parent


class DeviSpareAgent:
    target: None | str = None

    def __init__(self, devispare_host: str, devispare_token: str) -> None:
        if self.target is None:
            raise RuntimeError(
                f"{self.__class__.__name__} has not a pre-defined target"
            )

        self._job: None | JobInfo = None

        api_client = ApiClient(
            Configuration(
                host=devispare_host,
                access_token=devispare_token,
            )
        )

        self._jobs = JobsApi(api_client)

    def run(
        self,
        tmp: Path,
        firmware: str,
        host: str,
        port: int,
        cafile: Path,
        certfile: Path,
        keyfile: Path,
        onwire_schema: OnWireSchema,
    ) -> None:
        https_ca_cert = BASE_DIR.joinpath("resources/mozilla-root-ca.pem").read_bytes()
        mqtt_ca_cert = cafile.read_bytes()
        client_key = keyfile.read_bytes()
        client_cert = certfile.read_bytes()

        base64_ca_cert = b64encode(mqtt_ca_cert + https_ca_cert).decode("utf-8")
        base64_client_cert = b64encode(client_cert).decode("utf-8")
        base64_client_key = b64encode(client_key).decode("utf-8")

        fw_tar = Path(firmware)

        if not (fw_tar.is_file() and tarfile.is_tarfile(fw_tar)):
            fw_tar = tmp / f"{uuid4()}.tar.gz"

            with fw_tar.open(mode="w") as tar:
                subprocess.run(
                    [
                        "docker",
                        "run",
                        "--rm",
                        firmware,
                        "tar",
                        "cj",
                        "bootloader.bin",
                        "partitions.bin",
                        "nuttx.bin",
                    ],
                    check=True,
                    stdout=tar,
                )

        bootloader = read_bin_base64_from_firmware(fw_tar, "bootloader.bin")
        partitions = read_bin_base64_from_firmware(fw_tar, "partitions.bin")
        nuttx = read_bin_base64_from_firmware(fw_tar, "nuttx.bin")

        file_system = LittleFS(
            block_size=4096,
            block_count=32,
            read_size=256,
            prog_size=256,
            disk_version=0x00020000,
        )

        evp_data = b64encode(file_system.context.buffer).decode("utf-8")

        deployment = Deployment(
            device_serial_number=str(uuid4()),
            evp_mqtt_endpoint={
                "host": host,
                "port": port,
            },
            certs={
                "ca_cert": base64_ca_cert,
                "client_cert": base64_client_cert,
                "client_key": base64_client_key,
            },
            target=self.target,
            firmware={
                "bootloader": {
                    "image": bootloader,
                },
                "partition_table": {
                    "address": 0xD000,
                    "image": partitions,
                },
                "partition_images": [
                    {"name": "evp_data", "image": evp_data},
                ],
            },
            flash_images=[
                {"address": 0x20000, "image": nuttx},
                {"address": 0x320000, "image": nuttx},
            ],
            iot_platform=onwire_schema.platform,
        )

        response = self._jobs.create_job(deployment)

        if response.status != ResponseStatus.SUCCESS:
            raise RuntimeError(f"Failed to create DeviSpare Job: {response.to_dict()}")

        self._job = response.result

        logging.info("Wait remote agent to be ready (this will take about 5 minutes)")

        self._wait(JobStatus.RUNNING)

    def stop(self, logs_folder: Path) -> None:
        if self._job:
            self._job = send_request_until_succeed(
                request=self._jobs.delete_job,
                args=[self._job.id],
            )

            self._wait(JobStatus.DONE)

            response = send_request_until_succeed(
                request=self._jobs.get_job_logs,
                args=[self._job.id],
            )

            for entry in response.logs:
                path = logs_folder / f"{entry.name.value}.txt"
                path.write_text(entry.log)

    def _wait(self, status: Literal["done", "running"]) -> None:
        if not self._job:
            raise Exception("A Job must exists to wait.")

        # Launch Job will take about 5 minutes for Type3 devices
        intervals = itertools.chain(
            [
                1,
                1,
                1,
                2,
                5,  # 10 seconds
                10,
                10,
                10,  # 30 seconds
            ],
            itertools.cycle([30]),
        )

        for interval in intervals:
            if self._job.job_status == JobStatus.ERROR:
                break

            if self._job.job_status == status:
                return

            time.sleep(interval)

            self._job = send_request_until_succeed(
                request=self._jobs.get_job_info,
                args=[self._job.id],
            )

            logging.info(
                f'jobid={self._job.id}, status={self._job.job_status or "N/A"} (waiting for status={status})'
            )

        raise RuntimeError(
            f"Expected jobid={self._job.id} status to be {status} but is {self._job.job_status}"
        )


def read_bin_base64_from_firmware(tar_file: Path, file_name: str) -> str:
    with tarfile.open(str(tar_file)) as tar:
        member = next(member for member in tar.getmembers() if file_name in member.name)
        file = tar.extractfile(member)
        if file:
            return b64encode(file.read()).decode("utf-8")
        raise Exception("Membre not found inside .tar file")


class T3WS(DeviSpareAgent):
    target = "xtensa-t3ws-esp32"


class T3P(DeviSpareAgent):
    target = "xtensa-t3p-esp32"


def send_request_until_succeed(request: Callable, args: list[Any]) -> Any:
    for _i in range(10):
        try:
            response = request(*args)
        except Exception:
            continue
        if response.status == ResponseStatus.SUCCESS:
            return cast(BaseModel, response.result)
        time.sleep(1)
    raise RuntimeError(f"DeviSpare API failed: {response.to_dict()}")
