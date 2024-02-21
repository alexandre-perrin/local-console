from pathlib import Path

from hypothesis import strategies as st
from wedge_cli.core.schemas import AgentConfiguration
from wedge_cli.core.schemas import EVPParams
from wedge_cli.core.schemas import IPAddress
from wedge_cli.core.schemas import MQTTParams
from wedge_cli.core.schemas import TLSConfiguration
from wedge_cli.core.schemas import WebserverParams


@st.composite
def generate_identifiers(
    draw: st.DrawFn,
    max_size: int,
    categories_first_char=("Ll", "Lu", "Nd"),
    categories_next_chars=("Ll", "Lu", "Nd"),
    include_in_first_char="",
    include_in_next_chars="",
    codec="ascii",
) -> str:
    """
    Generates strings whose first character can have different settings
    than the remaining characters.

    Initial usages of the `from_regex` built-in strategy incurred in
    run times that exceeded the Hypothesis' deadline, since that
    strategy performs a brute-force approach of generating arbitrarily
    long strings, then filtering them out via the regex.
    It's an inefficient approach overall.
    """
    assert max_size > 0
    return draw(
        st.tuples(
            st.characters(
                codec=codec,
                categories=categories_first_char,
                include_characters=include_in_first_char,
            ),
            st.lists(
                st.characters(
                    codec=codec,
                    categories=categories_next_chars,
                    include_characters=include_in_next_chars,
                ),
                max_size=max_size - 1,
            ),
        ).map(lambda t: t[0] + "".join(t[1]))
    )


@st.composite
def generate_valid_ip(draw: st.DrawFn) -> str:
    return draw(generate_identifiers(max_size=10, include_in_next_chars="-."))


@st.composite
def generate_invalid_ip(draw: st.DrawFn) -> str:
    return draw(
        generate_identifiers(
            max_size=10, categories_first_char=("S", "Z"), include_in_first_char=" +"
        )
    )


@st.composite
def generate_valid_port_number(draw: st.DrawFn) -> int:
    return draw(st.integers(min_value=0, max_value=65535))


@st.composite
def generate_agent_config(draw: st.DrawFn) -> AgentConfiguration:
    return AgentConfiguration(
        evp=EVPParams(
            iot_platform=draw(
                generate_identifiers(max_size=10, categories_first_char=("Ll", "Lu"))
            ),
        ),
        mqtt=MQTTParams(
            host=IPAddress(ip_value=draw(generate_valid_ip())),
            port=draw(generate_valid_port_number()),
            device_id=draw(
                generate_identifiers(
                    max_size=10,
                    categories_first_char=("Ll", "Lu"),
                    include_in_first_char="_",
                    include_in_next_chars="-",
                )
            ),
        ),
        webserver=WebserverParams(
            host=IPAddress(ip_value=draw(generate_valid_ip())),
            port=draw(generate_valid_port_number()),
        ),
        tls=TLSConfiguration.model_construct(
            ca_certificate=draw(st.none()),
            ca_key=draw(st.none()),
        ),
    )


@st.composite
def generate_tls_config(draw: st.DrawFn) -> TLSConfiguration:
    return TLSConfiguration.model_construct(
        ca_certificate=draw(st.just(Path("ca.crt"))),
        ca_key=draw(st.just(Path("ca.key"))),
    )
