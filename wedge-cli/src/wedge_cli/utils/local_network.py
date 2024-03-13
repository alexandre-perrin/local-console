import ipaddress
import socket


def get_my_ip_by_routing(probe_host: str = "9.9.9.9") -> str:
    """
    This gets the machine's IP by means of a traceroute
    command to a stable public service such as Quad9 DNS.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((probe_host, 53))
    this_machine_ip = str(s.getsockname()[0])
    s.close()
    return this_machine_ip


LOCAL_IP: str = get_my_ip_by_routing()


def is_localhost(hostname: str) -> bool:
    resolved_ip = socket.gethostbyname(hostname)
    return ipaddress.ip_address(resolved_ip).is_loopback


def replace_local_address(hostname: str) -> str:
    host = hostname
    if is_localhost(host):
        host = LOCAL_IP
    return host
