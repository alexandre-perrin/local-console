import argparse
import json
import logging
import socket
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from process_handler import ProcessHandler
from process_handler import SharedLogger
from retry import retry
from wedge_cli.utils.tls import generate_self_signed_ca

FORMAT = "%(asctime)s %(levelname)s %(message)s"
logging.basicConfig(format=FORMAT, level=logging.DEBUG)
log = logging.getLogger()


def parse_test_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--with-tls",
        action="store_true",
        help="Whether to exercise the TLS infrastructure",
    )

    return parser.parse_args()


@retry(tries=5, exceptions=AssertionError)
def check_rpc_telemetry(telemetry: subprocess.Popen, wedge_cli_pre: list[str]) -> None:
    # send rpc
    # 000FF1 = (0,15,241)
    subprocess.run(wedge_cli_pre + ["rpc", "node", "my-method", '{"rgb":"000FF1"}'])
    time.sleep(2)
    for line in telemetry.stdout:  # type: ignore
        telemetry_out = json.loads(line.replace("'", '"'))
        rgb = (
            telemetry_out["node/my-topic"]["r"],
            telemetry_out["node/my-topic"]["g"],
            telemetry_out["node/my-topic"]["b"],
        )

        assert rgb == ("0", "15", "241")
        telemetry.kill()
        break


@retry(tries=5, exceptions=AssertionError)
def check_deploy_empty(deployment: subprocess.Popen, wedge_cli_pre: list[str]) -> None:
    try:
        subprocess.run(
            wedge_cli_pre + ["deploy", "-e"], capture_output=True, text=True, check=True
        )
    except subprocess.CalledProcessError as e:
        log.error("Deploying failed like: %s", e.stderr)
        raise e

    time.sleep(2)
    for i, line in enumerate(deployment.stdout):  # type: ignore
        if "'instances': {}, 'modules': {}" in line:
            deployment.kill()
            return
        assert i < 10, "Deployment status not empty yet"


def build_and_deploy_app(app_dir: Path, wedge_cli_pre: list[str]) -> None:
    # Build app
    subprocess.run(wedge_cli_pre + ["build"], cwd=app_dir, check=True)

    # Deploy app
    deploy = subprocess.run(
        wedge_cli_pre + ["deploy", "--timeout", "60"],
        cwd=app_dir,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "WARNING" not in deploy.stdout
    assert deploy.returncode == 0, f"Error during deploy: {deploy.stderr}"


def setup_tls(tls_files_dir: Path, wedge_cli_pre: list[str]) -> None:
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
        wedge_cli_pre
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
        wedge_cli_pre + ["config", "set", "tls", "ca_key", str(ca_key_path.resolve())],
        check=True,
    )
    # TCP port is configured by the broker preparation


def setup_no_tls(wedge_cli_pre: list[str]):
    # Configure the CLI to avoid TLS
    subprocess.run(
        wedge_cli_pre
        + [
            "config",
            "unset",
            "tls",
            "ca_certificate",
        ],
        check=True,
    )
    subprocess.run(
        wedge_cli_pre + ["config", "unset", "tls", "ca_key"],
        check=True,
    )


class LocalBroker(ProcessHandler):
    def __init__(
        self,
        with_tls: bool,
        tmp_dir: Path,
        log_handler: logging.Logger,
        wedge_cli_pre: list[str],
    ) -> None:
        super().__init__(log_handler)

        self.cmdline = wedge_cli_pre + ["broker", "cool_mqtt_broker"]
        self.prepare(with_tls, wedge_cli_pre)

    def prepare(self, with_tls: bool, wedge_cli_pre: list[str]) -> None:
        # Configure TCP port
        self._port = 8883 if with_tls else 1883
        subprocess.run(
            wedge_cli_pre + ["config", "set", "mqtt", "port", str(self._port)],
            check=True,
        )
        self._host = "localhost"
        subprocess.run(
            wedge_cli_pre + ["config", "set", "mqtt", "host", self._host],
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
    def __init__(self, log_handler: logging.Logger, wedge_cli_pre: list[str]) -> None:
        super().__init__(log_handler)
        self.cmdline = wedge_cli_pre + ["start"]
        self.options = {}

    def start_check(self) -> None:
        pass


@contextmanager
def wedge_area(with_tls: bool) -> None:
    with TemporaryDirectory() as _tempdir:
        tmp_dir = Path(_tempdir)
        config_dir = tmp_dir / "config"
        cmd_preamble = ["wedge-cli", "-d", "--config-dir", str(config_dir)]

        if with_tls:
            tls_dir = tmp_dir / "tls"
            setup_tls(tls_dir, cmd_preamble)
        else:
            setup_no_tls(cmd_preamble)

        yield tmp_dir, cmd_preamble


def main() -> None:
    args = parse_test_arguments()
    app_dir = Path("samples/rpc-example")
    with_tls = args.with_tls

    try:
        with (
            wedge_area(with_tls) as (tmp_dir, cmd_preamble),
            SharedLogger() as slog,
            LocalBroker(with_tls, tmp_dir, slog, cmd_preamble),
            LocalAgent(slog, cmd_preamble),
        ):
            build_and_deploy_app(app_dir, cmd_preamble)
            log.info("Deployed module successfully")

            telemetry = subprocess.Popen(
                cmd_preamble + ["get", "telemetry"],
                stdout=subprocess.PIPE,
                text=True,
            )
            check_rpc_telemetry(telemetry, cmd_preamble)
            log.info("Telemetry arrived succesfully")

            deployment = subprocess.Popen(
                cmd_preamble + ["get", "deployment"],
                stdout=subprocess.PIPE,
                text=True,
            )
            check_deploy_empty(deployment, cmd_preamble)
            log.info("Deployment emptied successfully")

        log.info("######################")
        log.info("#  Test successful!  #")
        log.info("######################")

    except (subprocess.CalledProcessError, ValueError) as e:
        log.error("Execution failed: %s", e)

    except KeyboardInterrupt:
        log.info("Cancelling")


if __name__ == "__main__":
    main()
