from pathlib import Path
from typing import Optional

from local_console.core.camera.enums import FirmwareExtension
from local_console.core.camera.enums import OTAUpdateModule
from local_console.core.camera.state import CameraState
from local_console.core.commands.ota_deploy import get_package_hash
from local_console.gui.model.camera_proxy import CameraStateProxy
from local_console.utils.validation import validate_imx500_model_file


def bind_connections(proxy: CameraStateProxy, camera_state: CameraState) -> None:
    proxy.bind_state_to_proxy("local_ip", camera_state)
    proxy.bind_state_to_proxy("mqtt_host", camera_state)
    proxy.bind_state_to_proxy("mqtt_port", camera_state)
    proxy.bind_state_to_proxy("ntp_host", camera_state)
    proxy.bind_state_to_proxy("ip_address", camera_state)
    proxy.bind_state_to_proxy("subnet_mask", camera_state)
    proxy.bind_state_to_proxy("gateway", camera_state)
    proxy.bind_state_to_proxy("dns_server", camera_state)
    proxy.bind_state_to_proxy("wifi_ssid", camera_state)
    proxy.bind_state_to_proxy("wifi_password", camera_state)

    # to propagate initialization in `CameraState`
    proxy.bind_state_to_proxy("is_connected", camera_state)


def bind_core_variables(proxy: CameraStateProxy, camera_state: CameraState) -> None:
    proxy.bind_state_to_proxy("is_ready", camera_state)
    proxy.bind_state_to_proxy("is_streaming", camera_state)
    proxy.bind_state_to_proxy("device_config", camera_state)


def bind_stream_variables(proxy: CameraStateProxy, camera_state: CameraState) -> None:
    # Proxy->State because we want the user to set this value via the GUI
    proxy.bind_proxy_to_state("roi", camera_state)

    # State->Proxy because this is either read from the device camera_state
    # or from states computed within the GUI code
    proxy.bind_state_to_proxy("stream_status", camera_state)


def bind_ai_model_function(proxy: CameraStateProxy, camera_state: CameraState) -> None:
    # Proxy->State because we want the user to set this value via the GUI
    proxy.bind_proxy_to_state("ai_model_file", camera_state, Path)

    # State->Proxy because this is computed from the model file
    proxy.bind_state_to_proxy("ai_model_file_valid", camera_state)

    def validate_file(current: Optional[Path], previous: Optional[Path]) -> None:
        if current:
            camera_state.ai_model_file_valid.value = validate_imx500_model_file(current)

    camera_state.ai_model_file.subscribe(validate_file)


def bind_firmware_file_functions(
    proxy: CameraStateProxy, camera_state: CameraState
) -> None:
    # Proxy->State because we want the user to set these values via the GUI
    proxy.bind_proxy_to_state("firmware_file", camera_state, Path)
    proxy.bind_proxy_to_state("firmware_file_version", camera_state)
    proxy.bind_proxy_to_state("firmware_file_type", camera_state)
    # Default value that matches the default widget selection
    proxy.firmware_file_type = OTAUpdateModule.APFW

    # State->Proxy because these are computed from the firmware_file
    proxy.bind_state_to_proxy("firmware_file_valid", camera_state)
    proxy.bind_state_to_proxy("firmware_file_hash", camera_state)

    def validate_file(current: Optional[Path], previous: Optional[Path]) -> None:
        if current:
            is_valid = True
            if camera_state.firmware_file_type.value == OTAUpdateModule.APFW:
                if current.suffix != FirmwareExtension.APPLICATION_FW:
                    is_valid = False
            else:
                if current.suffix != FirmwareExtension.SENSOR_FW:
                    is_valid = False

            camera_state.firmware_file_hash.value = (
                get_package_hash(current) if is_valid else ""
            )
            camera_state.firmware_file_valid.value = is_valid

    camera_state.firmware_file.subscribe(validate_file)


def bind_input_directories(proxy: CameraStateProxy, camera_state: CameraState) -> None:
    proxy.bind_state_to_proxy("image_dir_path", camera_state, str)
    proxy.bind_state_to_proxy("inference_dir_path", camera_state, str)


def bind_vapp_file_functions(
    proxy: CameraStateProxy, camera_state: CameraState
) -> None:
    proxy.bind_proxy_to_state("vapp_config_file", camera_state)
    proxy.bind_proxy_to_state("vapp_labels_file", camera_state)
    proxy.bind_proxy_to_state("vapp_type", camera_state)

    # `vapp_schema_file` is not bound because it is important that the chosen
    # file undergoes thorough validation before being committed.

    # The labels map is computed from the labels file,
    # so data binding must be state-->proxy.
    proxy.bind_state_to_proxy("vapp_labels_map", camera_state, str)


def bind_app_module_functions(
    proxy: CameraStateProxy, camera_state: CameraState
) -> None:
    # State->Proxy because these are either read from the device state
    # or from states computed within the camera tracking
    proxy.bind_state_to_proxy("deploy_status", camera_state)
    proxy.bind_state_to_proxy("deploy_stage", camera_state)
    proxy.bind_state_to_proxy("deploy_operation", camera_state)

    # Proxy->State because we want the user to set this value via the GUI
    proxy.bind_proxy_to_state("module_file", camera_state, Path)
