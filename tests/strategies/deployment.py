from hypothesis import strategies as st
from wedge_cli.core.schemas import Deployment
from wedge_cli.core.schemas import DeploymentManifest
from wedge_cli.core.schemas import InstanceSpec
from wedge_cli.core.schemas import Module
from wedge_cli.core.schemas import Topics


@st.composite
def instance_spec_strategy(draw):
    return InstanceSpec(
        moduleId=draw(st.text(min_size=1, max_size=5)),
        subscribe=draw(
            st.dictionaries(
                st.text(min_size=1, max_size=5),
                st.text(max_size=5),
                min_size=1,
                max_size=5,
            )
        ),
        publish=draw(
            st.dictionaries(
                st.text(min_size=1, max_size=5),
                st.text(max_size=5),
                min_size=1,
                max_size=5,
            )
        ),
    )


@st.composite
def module_strategy(draw):
    return Module(
        entryPoint=draw(st.text(min_size=1, max_size=5)),
        moduleImpl=draw(st.text(min_size=1, max_size=5)),
        downloadUrl=draw(st.text(min_size=1, max_size=5)),
        hash=draw(st.text(min_size=1, max_size=5)),
    )


@st.composite
def topics_strategy(draw):
    return Topics(
        type=draw(st.text(min_size=1, max_size=5)),
        topic=draw(st.text(min_size=1, max_size=5)),
    )


@st.composite
def deployment_strategy(draw):
    return Deployment(
        deploymentId=draw(st.text(min_size=1, max_size=5)),
        instanceSpecs=draw(
            st.dictionaries(
                st.text(min_size=1, max_size=5),
                instance_spec_strategy(),
                min_size=1,
                max_size=5,
            )
        ),
        modules=draw(
            st.dictionaries(
                st.text(min_size=1, max_size=5),
                module_strategy(),
                min_size=1,
                max_size=5,
            )
        ),
        publishTopics=draw(
            st.dictionaries(
                st.text(min_size=1, max_size=5),
                topics_strategy(),
                min_size=1,
                max_size=5,
            )
        ),
        subscribeTopics=draw(
            st.dictionaries(
                st.text(min_size=1, max_size=5),
                topics_strategy(),
                min_size=1,
                max_size=5,
            )
        ),
    )


@st.composite
def deployment_manifest_strategy(draw):
    return DeploymentManifest(deployment=draw(deployment_strategy()))
