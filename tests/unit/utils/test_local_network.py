from unittest.mock import MagicMock
from unittest.mock import patch

from hypothesis import given
from local_console.utils.local_network import get_my_ip_by_routing
from local_console.utils.local_network import is_localhost
from local_console.utils.local_network import LOCAL_IP
from local_console.utils.local_network import replace_local_address

from tests.strategies.configs import generate_invalid_ip
from tests.strategies.configs import generate_text
from tests.strategies.configs import generate_valid_port_number


@given(generate_invalid_ip(), generate_valid_port_number())
def test_get_my_ip_by_routing(ip: str, port: int):
    mock_socket = MagicMock()
    mock_socket.socket.return_value.getsockname.return_value = (ip, port)
    with patch("local_console.utils.local_network.socket", mock_socket):
        assert get_my_ip_by_routing() == ip
        mock_socket.socket.assert_called_once_with(
            mock_socket.AF_INET, mock_socket.SOCK_DGRAM
        )
        mock_socket.socket.return_value.connect.assert_called_once_with(("9.9.9.9", 53))
        mock_socket.socket.return_value.close.assert_called_once()


@given(generate_invalid_ip(), generate_valid_port_number())
def test_get_my_ip_by_routing_no_connection(ip: str, port: int):
    mock_socket = MagicMock()
    mock_socket.socket.return_value.getsockname.return_value = (ip, port)
    mock_socket.socket.return_value.connect.side_effect = OSError("Connection Failed")
    with patch("local_console.utils.local_network.socket", mock_socket):
        assert get_my_ip_by_routing() == ""
        mock_socket.socket.assert_called_once_with(
            mock_socket.AF_INET, mock_socket.SOCK_DGRAM
        )
        mock_socket.socket.return_value.connect.assert_called_once_with(("9.9.9.9", 53))
        mock_socket.socket.return_value.getsockname.assert_not_called()
        mock_socket.socket.return_value.close.assert_not_called()


def test_is_localhost():
    assert is_localhost("localhost")
    assert is_localhost("127.0.0.1")


@given(
    generate_text(),
)
def test_is_localhost_fail(hostname: str):
    assert not is_localhost("192.168.1.1.1")
    assert not is_localhost("192.168.1.1")
    assert not is_localhost(f"{hostname}.")
    assert not is_localhost("".join(map(str, range(10000))))
    with patch(
        "local_console.utils.local_network.socket.gethostbyname", side_effects=Exception
    ):
        assert not is_localhost(hostname)


@given(
    generate_text(),
)
def test_replace_local_address(hostname: str):
    assert replace_local_address("localhost") == LOCAL_IP
    hostname = f"{hostname}."
    assert not is_localhost(hostname) == hostname
