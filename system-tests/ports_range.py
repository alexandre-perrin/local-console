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
import concurrent.futures
import socket
import sys
from collections.abc import Iterable
from random import sample


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scans a port range and returns two closed ports"
    )
    parser.add_argument("host", type=str, help="Target host")
    parser.add_argument(
        "start_port", type=int, help="Starting port in the port range to scan"
    )
    parser.add_argument(
        "end_port",
        type=int,
        help="Ending port in the port range to scan (included in the range)",
    )
    parser.add_argument(
        "-e",
        "--exclude",
        type=int,
        action="append",
        help="Port within the range to skip. Several can be set.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    print("Running with:", args, file=sys.stderr)

    port_range = set(range(args.start_port, args.end_port + 1)) - set(args.exclude)
    open_ports = port_scanner(args.host, port_range)
    print("Open ports:", sorted(open_ports), file=sys.stderr)

    closed_ports = sorted(port_range - open_ports)
    chosen_ports = sample(closed_ports, 2)
    print(*chosen_ports)


def scan_port(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            s.connect((host, port))
            return True
        except Exception:
            return False


def port_scanner(host: str, port_range: Iterable[int]) -> set[int]:
    ports: set[int] = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        future_to_port = {
            executor.submit(scan_port, host, port): port for port in port_range
        }
        for future in concurrent.futures.as_completed(future_to_port):
            port = future_to_port[future]
            if future.result():
                ports.add(port)
    return ports


if __name__ == "__main__":
    main()
