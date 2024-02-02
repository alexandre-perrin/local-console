import json
import logging
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

import psutil
from retry import retry

FORMAT = "%(asctime)s %(levelname)s %(message)s"
logging.basicConfig(format=FORMAT, level=logging.DEBUG)
log = logging.getLogger()


def kill_agent() -> None:
    for proc in psutil.process_iter(attrs=["pid", "name"]):
        if "evp_agent" in proc.info["name"]:  # type: ignore
            proc.kill()


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
    for line in deployment.stdout:  # type: ignore
        assert "'instances': {}, 'modules': {}" in line
        deployment.kill()
        break


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
        with (wedge_area() as (tmp_dir, cmd_preamble),):
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
    finally:
        kill_agent()


if __name__ == "__main__":
    main()
