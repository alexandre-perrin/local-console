import ipaddress
import logging
import socket

logger = logging.getLogger(__file__)


def get_my_ip_by_routing(probe_host: str = "9.9.9.9") -> str:
    """
    This gets the machine's IP by means of a traceroute
    command to a stable public service such as Quad9 DNS.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((probe_host, 53))
        this_machine_ip = str(s.getsockname()[0])
        s.close()
    except OSError as e:
        logger.warning(f"Socket connect error: {e}")
        this_machine_ip = ""
    return this_machine_ip


LOCAL_IP: str = get_my_ip_by_routing()


def is_localhost(hostname: str) -> bool:
    try:
        resolved_ip = socket.gethostbyname(hostname)
        return ipaddress.ip_address(resolved_ip).is_loopback
    except socket.gaierror:
        return False
    except UnicodeError:
        # Raised when using very long strings
        return False
    except Exception as e:
        logger.warning(f"Unknown error while getting host by name: {e}")
    return False


def replace_local_address(hostname: str) -> str:
    return LOCAL_IP if is_localhost(hostname) else hostname


def is_valid_host(hostname: str) -> bool:
    try:
        socket.gethostbyname(hostname)
    except socket.gaierror as e:
        if e.errno == socket.EAI_NONAME:
            logger.warning(f"Invalid hostname or IP address - {hostname}: {e}")
        elif e.errno == socket.EAI_AGAIN:
            logger.warning(f"DNS look up error - {hostname}: {e}")
        else:
            logger.warning(f"Socket error - {hostname}: {e}")
        return False
    except Exception as e:
        logger.warning(f"An unexpected error occurred - {hostname}: {e}")
        return False
    return True
