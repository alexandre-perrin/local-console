import io
import logging
from pathlib import Path
from typing import Annotated
from typing import Optional

import qrcode
import typer
from wedge_cli.core.config import get_config
from wedge_cli.utils.local_network import get_my_ip_by_routing
from wedge_cli.utils.local_network import is_localhost

logger = logging.getLogger(__name__)

app = typer.Typer(
    help=(
        "Command to generate a QR code for camera onboarding. "
        "Host and port options default to the configured values in the CLI."
    )
)


@app.callback(invoke_without_command=True)
def qr(
    host: Annotated[
        Optional[str],
        typer.Option(help="Host address for the MQTT broker."),
    ] = None,
    port: Annotated[
        Optional[int],
        typer.Option(help="TCP port on which the MQTT broker is listening"),
    ] = None,
    enable_tls: Annotated[
        Optional[bool],
        typer.Option(help="Whether to connect using TLS"),
    ] = None,
    ntp_server: Annotated[
        str,
        typer.Option(help="NTP server to connect to for time synchronization"),
    ] = "pool.ntp.org",
    save_png: Annotated[
        Optional[Path],
        typer.Option(help="PNG file name to which save QR code to"),
    ] = None,
) -> None:
    # Take default values from the configured settings
    config = get_config()
    host = config.mqtt.host.ip_value if not host else host
    port = config.mqtt.port if not port else port
    tls_enabled = config.is_tls_enabled if enable_tls is None else enable_tls

    local_ip = get_my_ip_by_routing()
    if is_localhost(host) or host == local_ip:
        host = local_ip

    # This verbosity is to blame between types-qrcode and mypy
    # It should be instead: qr_code = qrcode.QRCode(...
    qr_code: qrcode.main.QRCode = qrcode.main.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        border=5,
    )
    qr_code.add_data(camera_qr_string(host, port, tls_enabled, ntp_server))
    qr_code.make(fit=True)

    if save_png:
        img = qr_code.make_image(fill_color="black", back_color="white")
        img.save(save_png.expanduser())

    # Print the code in the terminal
    f = io.StringIO()
    qr_code.print_ascii(out=f)
    f.seek(0)
    print(f.read())


def camera_qr_string(
    mqtt_host: str, mqtt_port: int, tls_enabled: bool, ntp_server: str
) -> str:
    tls_flag = 0 if tls_enabled else 1
    return f"AAIAAAAAAAAAAAAAAAAAAA==N=11;E={mqtt_host};H={mqtt_port};t={tls_flag};T={ntp_server};U1FS"
