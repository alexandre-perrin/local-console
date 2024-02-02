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

FORMAT = "%(asctime)s %(levelname)s %(message)s"
logging.basicConfig(format=FORMAT, level=logging.DEBUG)
log = logging.getLogger()


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
            break
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


class LocalBroker(ProcessHandler):
    def __init__(
        self,
        tmp_dir: Path,
        log_handler: logging.Logger,
        wedge_cli_pre: list[str],
    ) -> None:
        super().__init__(log_handler)

        mosquitto_dir = Path(__file__).parents[1] / ".devcontainer"
        conf_file_name = "mosquitto.conf"
        conf_file = mosquitto_dir / conf_file_name
        assert conf_file.is_file()

        self.cmdline = ["mosquitto", "-c", str(conf_file.resolve())]
        self.options = {"cwd": tmp_dir}

        self.prepare(wedge_cli_pre)

    def prepare(self, wedge_cli_pre: list[str]) -> None:
        # Configure TCP port
        self._port = 1883
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
def wedge_area() -> None:
    with TemporaryDirectory() as _tempdir:
        tmp_dir = Path(_tempdir)
        config_dir = tmp_dir / "config"
        cmd_preamble = ["wedge-cli", "-d", "--config-dir", str(config_dir)]

        yield tmp_dir, cmd_preamble


def main() -> None:
    app_dir = Path("samples/rpc-example")

    try:
        with (
            wedge_area() as (tmp_dir, cmd_preamble),
            SharedLogger() as slog,
            LocalBroker(tmp_dir, slog, cmd_preamble),
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

        log.info("Test successful!")

    except subprocess.CalledProcessError as e:
        log.error("Execution failed: %s", e)
    except KeyboardInterrupt:
        log.info("Cancelling")


if __name__ == "__main__":
    main()
