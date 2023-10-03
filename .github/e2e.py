import json
import os
import subprocess
import time

import psutil
from retry import retry


def kill_agent() -> None:
    for proc in psutil.process_iter(attrs=["pid", "name"]):
        if "evp_agent" in proc.info["name"]:  # type: ignore
            proc.kill()


@retry(tries=5, exceptions=AssertionError)
def check_rpc_telemetry(telemetry: subprocess.Popen) -> None:
    # send rpc
    # 000FF1 = (0,15,241)
    subprocess.run(["wedge-cli", "rpc", "node", "my-method", '{"rgb":"000FF1"}'])
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
def check_deploy_empty(deployment: subprocess.Popen) -> None:
    subprocess.run(
        ["wedge-cli", "-v", "deploy", "-e"],
        capture_output=True,
        text=True,
    )
    time.sleep(2)
    for line in deployment.stdout:  # type: ignore
        assert "'instances': {}, 'modules': {}" in line
        deployment.kill()
        break


def start_deploy_build() -> None:
    env = os.environ.copy()
    # start_agent
    subprocess.Popen(["wedge-cli", "start"], env=env)

    # build and deploy, wait necessary to give time for wasms to build
    os.chdir("samples/rpc-example")
    subprocess.run(["wedge-cli", "-v", "build"])
    time.sleep(3)
    deploy = subprocess.run(
        ["wedge-cli", "-v", "deploy", "--timeout", "60"],
        capture_output=True,
        text=True,
    )
    assert "WARNING" not in deploy.stdout


def main() -> None:
    try:
        start_deploy_build()
    except OSError:
        kill_agent()
        raise Exception("Test failed: before deployment arrived")
    except AssertionError:
        kill_agent()
        raise Exception("Deployment timed out before arriving")

    try:
        # get telemetry - check
        telemetry = subprocess.Popen(
            ["wedge-cli", "get", "telemetry"],
            stdout=subprocess.PIPE,
            universal_newlines=True,
        )

        check_rpc_telemetry(telemetry)
        print("Telemetry arrived succesfully")

        deployment = subprocess.Popen(
            ["wedge-cli", "get", "deployment"],
            stdout=subprocess.PIPE,
            universal_newlines=True,
        )

        check_deploy_empty(deployment)
    except Exception:
        kill_agent()

    kill_agent()
    print("Deployment empty")
    print("Test successful!")


if __name__ == "__main__":
    main()
