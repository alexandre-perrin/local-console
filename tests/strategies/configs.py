import re

from hypothesis import strategies as st
from wedge_cli.utils.schemas import AgentConfiguration
from wedge_cli.utils.schemas import EVPParams
from wedge_cli.utils.schemas import IPAddress
from wedge_cli.utils.schemas import MQTTParams
from wedge_cli.utils.schemas import WebserverParams


@st.composite
def generate_valid_ip(draw) -> str:
    return str(draw(st.from_regex(re.compile(r"^[\.\w-]+$"))))


@st.composite
def generate_agent_config(draw) -> AgentConfiguration:
    return AgentConfiguration(
        evp=EVPParams(
            iot_platform=draw(st.text(min_size=1, max_size=10)),
            version=draw(st.text(min_size=1, max_size=10)),
        ),
        mqtt=MQTTParams(
            host=IPAddress(ip_value=draw(generate_valid_ip())),
            port=draw(st.integers()),
            device_id=draw(st.text(min_size=1, max_size=10)),
        ),
        webserver=WebserverParams(
            host=IPAddress(ip_value=draw(generate_valid_ip())), port=draw(st.integers())
        ),
    )
