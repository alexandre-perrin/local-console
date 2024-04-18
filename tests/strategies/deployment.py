from hypothesis import strategies as st
from wedge_cli.core.schemas.schemas import Deployment
from wedge_cli.core.schemas.schemas import DeploymentManifest
from wedge_cli.core.schemas.schemas import InstanceSpec
from wedge_cli.core.schemas.schemas import Module
from wedge_cli.core.schemas.schemas import Topics

from tests.strategies.configs import generate_text


@st.composite
def instance_spec_strategy(draw):
    return InstanceSpec(
        moduleId=draw(generate_text()),
        subscribe=draw(
            st.dictionaries(
                generate_text(),
                generate_text(),
                min_size=1,
                max_size=5,
            )
        ),
        publish=draw(
            st.dictionaries(
                generate_text(),
                generate_text(),
                min_size=1,
                max_size=5,
            )
        ),
    )


@st.composite
def module_strategy(draw):
    return Module(
        entryPoint=draw(generate_text()),
        moduleImpl=draw(generate_text()),
        downloadUrl=draw(generate_text()),
        hash=draw(generate_text()),
    )


@st.composite
def topics_strategy(draw):
    return Topics(
        type=draw(generate_text()),
        topic=draw(generate_text()),
    )


@st.composite
def deployment_strategy(draw):
    return Deployment(
        deploymentId=draw(generate_text()),
        instanceSpecs=draw(
            st.dictionaries(
                generate_text(),
                instance_spec_strategy(),
                min_size=1,
                max_size=5,
            )
        ),
        modules=draw(
            st.dictionaries(
                generate_text(),
                module_strategy(),
                min_size=1,
                max_size=5,
            )
        ),
        publishTopics=draw(
            st.dictionaries(
                generate_text(),
                topics_strategy(),
                min_size=1,
                max_size=5,
            )
        ),
        subscribeTopics=draw(
            st.dictionaries(
                generate_text(),
                topics_strategy(),
                min_size=1,
                max_size=5,
            )
        ),
    )


@st.composite
def deployment_manifest_strategy(draw):
    return DeploymentManifest(deployment=draw(deployment_strategy()))
