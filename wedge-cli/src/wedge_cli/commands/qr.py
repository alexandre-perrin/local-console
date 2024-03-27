import io
import logging
from pathlib import Path
from typing import Annotated
from typing import Optional

import typer
from wedge_cli.core.camera import get_qr_object
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
    port = config.mqtt.port if port is None else port
    tls_enabled = config.is_tls_enabled if enable_tls is None else enable_tls

    local_ip = get_my_ip_by_routing()
    if is_localhost(host) or host == local_ip:
        host = local_ip

    qr_code = get_qr_object(host, port, tls_enabled, ntp_server)
    if save_png:
        img = qr_code.make_image(fill_color="black", back_color="white")
        img.save(save_png.expanduser())

    # Print the code in the terminal
    f = io.StringIO()
    qr_code.print_ascii(out=f)
    f.seek(0)
    print(f.read())
