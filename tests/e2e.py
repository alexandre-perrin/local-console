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
import argparse
import json
import logging
import re
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from local_console.core.schemas.schemas import OnWireProtocol
from local_console.utils.tls import generate_self_signed_ca
from process_handler import ProcessHandler
from process_handler import SharedLogger
from retry import retry

FORMAT = "%(asctime)s %(levelname)s %(message)s"
logging.basicConfig(format=FORMAT, level=logging.DEBUG)
log = logging.getLogger()


def parse_test_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-t",
        "--with-tls",
        action="store_true",
        help="Whether to exercise the TLS infrastructure",
    )
    parser.add_argument(
        "-s",
        "--ows-version",
        type=OnWireProtocol,
        choices=list(OnWireProtocol),
        default=OnWireProtocol.EVP2,
        help="Which on-wire schema version version to set the agent to",
    )

    return parser.parse_args()


@retry(tries=5, exceptions=AssertionError)
def check_rpc_telemetry(
    telemetry: subprocess.Popen, local_console_pre: list[str]
) -> None:
    # send rpc
    # 000FF1 = (0,15,241)
    subprocess.run(local_console_pre + ["rpc", "node", "my-method", '{"rgb":"000FF1"}'])
    time.sleep(2)
    log.info("Waiting to get telemetries")
    for line in telemetry.stdout:  # type: ignore
        telemetry_out = json.loads(line.replace("'", '"'))
        rgb = (
            telemetry_out["node/my-topic"]["r"],
            telemetry_out["node/my-topic"]["g"],
            telemetry_out["node/my-topic"]["b"],
        )

        assert rgb == ("0", "15", "241")
        break


def check_logs(local_console_pre: list[str]) -> None:
    log.info("Starting to get logs")
    logs = subprocess.Popen(
        local_console_pre + ["logs", "node"],
        stdout=subprocess.PIPE,
        text=True,
        bufsize=0,
    )
    log.info("Waiting for logs")
    for line in logs.stdout:  # type: ignore
        log.info(f"Getting logs: {line}")
        if "Sending telemetry..." in line:
            logs.kill()
            break


@retry(tries=5, exceptions=AssertionError)
def check_configuration_telemetry(
    telemetry: subprocess.Popen, local_console_pre: list[str]
) -> None:
    # send configuration, expect loopback over telemetry
    topic = "test-topic"
    payload = "some-payload"

    telemetry_topic = f"node/{topic}"

    subprocess.run(local_console_pre + ["config", "instance", "node", topic, payload])
    for i, line in enumerate(telemetry.stdout):  # type: ignore
        telemetry_out = json.loads(line.replace("'", '"'))
        obj = telemetry_out.get(telemetry_topic)
        if obj:
            # Example: {'node/test-topic': {'data': 'some-payload'}}
            assert "data" in obj
            assert obj["data"] == payload
            break
        assert i < 30, "Telemetry echo has not arrived yet"


@retry(tries=5, exceptions=AssertionError)
def check_deploy_empty(
    deployment: subprocess.Popen, local_console_pre: list[str]
) -> None:
    try:
        subprocess.run(
            local_console_pre + ["deploy", "-e"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        log.error("Deploying failed like: %s", e.stderr)
        raise e

    time.sleep(2)
    empty_regex = re.compile(r"""['"]instances['"]:\s*{},\s*['"]modules['"]:\s*{}""")
    for i, line in enumerate(deployment.stdout):  # type: ignore
        if empty_regex.search(line):
            deployment.kill()
            return
        assert i < 10, "Deployment status not empty yet"


def build_and_deploy_app(app_dir: Path, local_console_pre: list[str]) -> None:
    # Build app
    subprocess.run(local_console_pre + ["build"], cwd=app_dir, check=True)

    # Deploy app
    deploy = subprocess.run(
        local_console_pre + ["deploy", "--timeout", "60"],
        cwd=app_dir,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "WARNING" not in deploy.stdout
    assert deploy.returncode == 0, f"Error during deploy: {deploy.stderr}"


def setup_tls(tls_files_dir: Path, local_console_pre: list[str]) -> None:
    """
    The file paths of files generated here are relative
    to the directory where the MQTT broker configuration
    file expects to find them.
    """
    # Generate a dummy CA
    ca_dir = tls_files_dir / "ca"
    ca_dir.mkdir(exist_ok=True, parents=True)
    ca_cert_path, ca_key_path, ca_cert, ca_key = generate_self_signed_ca(ca_dir)

    # Configure the CLI with updated TLS parameters
    subprocess.run(
        local_console_pre
        + [
            "config",
            "set",
            "tls",
            "ca_certificate",
            str(ca_cert_path.resolve()),
        ],
        check=True,
    )
    subprocess.run(
        local_console_pre
        + ["config", "set", "tls", "ca_key", str(ca_key_path.resolve())],
        check=True,
    )
    # TCP port is configured by the broker preparation


def setup_no_tls(local_console_pre: list[str]):
    # Configure the CLI to avoid TLS
    subprocess.run(
        local_console_pre
        + [
            "config",
            "unset",
            "tls",
            "ca_certificate",
        ],
        check=True,
    )
    subprocess.run(
        local_console_pre + ["config", "unset", "tls", "ca_key"],
        check=True,
    )


def set_onwire_schema_version(
    onwire_schema: OnWireProtocol, local_console_pre: list[str]
) -> None:
    subprocess.run(
        local_console_pre
        + ["config", "set", "evp", "iot_platform", onwire_schema.for_agent_environ()],
        check=True,
    )


class LocalBroker(ProcessHandler):
    def __init__(
        self,
        with_tls: bool,
        tmp_dir: Path,
        log_handler: logging.Logger,
        local_console_pre: list[str],
    ) -> None:
        super().__init__(log_handler)

        self.cmdline = local_console_pre + ["broker", "cool_mqtt_broker"]
        self.prepare(with_tls, local_console_pre)

    def prepare(self, with_tls: bool, local_console_pre: list[str]) -> None:
        # Configure TCP port
        self._port = 8883 if with_tls else 1883
        subprocess.run(
            local_console_pre + ["config", "set", "mqtt", "port", str(self._port)],
            check=True,
        )
        self._host = "localhost"
        subprocess.run(
            local_console_pre + ["config", "set", "mqtt", "host", self._host],
            check=True,
        )

    @retry(
        tries=5,
        delay=0.5,
        exceptions=(
            ConnectionError,
            OSError,
        ),
    )
    def start_check(self, timeout: int = 1) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            # Try to connect to the host and port
            result = sock.connect_ex((self._host, self._port))
            # If the result is 0, the connection was successful
            if result != 0:
                raise ConnectionRefusedError
        finally:
            # Make sure to close the socket
            sock.close()


class LocalAgent(ProcessHandler):
    def __init__(
        self, log_handler: logging.Logger, local_console_pre: list[str]
    ) -> None:
        super().__init__(log_handler)
        self.cmdline = local_console_pre + ["start"]
        self.options = {}

    def start_check(self) -> None:
        pass


@contextmanager
def wedge_area(with_tls: bool, onwire_schema: OnWireProtocol) -> None:
    with TemporaryDirectory() as _tempdir:
        tmp_dir = Path(_tempdir)
        config_dir = tmp_dir / "config"
        cmd_preamble = ["local-console", "-v", "--config-dir", str(config_dir)]

        if with_tls:
            tls_dir = tmp_dir / "tls"
            setup_tls(tls_dir, cmd_preamble)
        else:
            setup_no_tls(cmd_preamble)

        set_onwire_schema_version(onwire_schema, cmd_preamble)

        yield tmp_dir, cmd_preamble


def main() -> None:
    args = parse_test_arguments()
    app_dir = Path("samples/rpc-example")
    with_tls = args.with_tls
    ows_version = args.ows_version

    retcode = 1
    try:
        with (
            wedge_area(with_tls, ows_version) as (tmp_dir, cmd_preamble),
            SharedLogger() as slog,
            LocalBroker(with_tls, tmp_dir, slog, cmd_preamble) as broker,
            LocalAgent(slog, cmd_preamble),
        ):
            build_and_deploy_app(app_dir, cmd_preamble)
            log.info("Deployed module successfully")

            telemetry = subprocess.Popen(
                cmd_preamble + ["get", "telemetry"],
                stdout=subprocess.PIPE,
                text=True,
                bufsize=0,
            )

            check_rpc_telemetry(telemetry, cmd_preamble)
            log.info("Telemetry for RPC arrived succesfully")

            check_logs(cmd_preamble)
            log.info("Logs arrived succesfully")

            check_configuration_telemetry(telemetry, cmd_preamble)
            log.info("Telemetry for Configuration arrived succesfully")
            telemetry.kill()

            deployment = subprocess.Popen(
                cmd_preamble + ["get", "deployment"],
                stdout=subprocess.PIPE,
                text=True,
            )
            check_deploy_empty(deployment, cmd_preamble)
            log.info("Deployment emptied successfully")

            # At this stage, it is safe to ignore abnormal broker termination
            broker.set_ignore_failure(True)

        log.info("######################")
        log.info("#  Test successful!  #")
        log.info("######################")
        retcode = 0

    except (subprocess.CalledProcessError, ValueError) as e:
        log.error("Execution failed: %s", e)

    except KeyboardInterrupt:
        log.info("Cancelling")

    return retcode


if __name__ == "__main__":
    sys.exit(main())
