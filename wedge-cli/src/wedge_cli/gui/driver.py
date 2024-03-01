import json
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from typing import Callable
from typing import Optional

import trio
from kivy.core.clipboard import Clipboard
from kivymd.app import MDApp
from wedge_cli.clients.agent import Agent
from wedge_cli.core.config import get_config
from wedge_cli.gui.camera import Camera
from wedge_cli.gui.Utility.axis_mapping import pixel_roi_from_normals
from wedge_cli.gui.Utility.axis_mapping import UnitROI
from wedge_cli.gui.Utility.sync_async import run_on_ui_thread
from wedge_cli.gui.Utility.sync_async import SyncAsyncBridge
from wedge_cli.servers.broker import spawn_broker
from wedge_cli.servers.webserver import AsyncWebserver
from wedge_cli.utils.local_network import LOCAL_IP

logger = logging.getLogger(__name__)


class Driver:
    def __init__(self, gui: type[MDApp], nursery: trio.Nursery) -> None:
        self.gui = gui
        self.nursery = nursery

        self.mqtt_client = Agent()
        self.upload_port = 0
        self.image_directory: Optional[Path] = None
        self.inferences_directory: Optional[Path] = None
        self.config = get_config()

        self.camera_state = Camera()
        self.start_flags = {
            "mqtt": trio.Event(),
            "webserver": trio.Event(),
        }

        self.bridge = SyncAsyncBridge()

    async def main(self) -> None:
        self.nursery.start_soon(self.mqtt_setup)
        self.nursery.start_soon(self.image_webserver_task)

        for flag in self.start_flags.values():
            await flag.wait()

        self.nursery.start_soon(self.gui_run)
        self.nursery.start_soon(self.bridge.bridge_listener)

    async def gui_run(self) -> None:
        await self.gui.async_run(async_lib="trio")
        self.bridge.close_task_queue()
        self.nursery.cancel_scope.cancel()

    async def mqtt_setup(self) -> None:
        async with (
            spawn_broker(self.config, self.nursery, False, "nicebroker"),
            self.mqtt_client.mqtt_scope(
                [
                    Agent.TELEMETRY_TOPIC,
                    Agent.RPC_RESPONSES_TOPIC,
                    Agent.ATTRIBUTES_TOPIC,
                ]
            ),
        ):
            self.start_flags["mqtt"].set()

            assert self.mqtt_client.client  # appease mypy
            async for msg in self.mqtt_client.client.messages():
                payload = json.loads(msg.payload)
                self.camera_state.process_incoming(msg.topic, payload)
                self.update_camera_status()
                logger.debug("Incoming on %s: %s", msg.topic, str(payload))

    def from_sync(self, async_fn: Callable, *args: Any) -> None:
        self.bridge.enqueue_task(async_fn, *args)

    @run_on_ui_thread
    def update_camera_status(self) -> None:
        self.gui.views[
            "streaming screen"
        ].model.stream_status = self.camera_state.sensor_state
    async def image_webserver_task(self) -> None:
        """
        Spawn a webserver on an arbitrary available port for receiving
        images from a camera.
        :param on_received: Callback that is triggered for each new received image
        :param base_dir: Path to directory where images will be saved into
        :return:
        """
        with (
            TemporaryDirectory(prefix="WEdgeGUI_") as tempdir,
            AsyncWebserver(
                Path(tempdir), port=0, on_incoming=self.process_camera_upload
            ) as image_serve,
        ):
            logger.info(f"Uploading data into {tempdir}")
            Clipboard.copy(tempdir)

            assert image_serve.port
            self.upload_port = image_serve.port
            self.image_directory = Path(tempdir) / "images"
            self.inferences_directory = Path(tempdir) / "inferences"
            self.image_directory.mkdir(exist_ok=True)
            self.inferences_directory.mkdir(exist_ok=True)

            self.start_flags["webserver"].set()
            await trio.sleep_forever()

    def process_camera_upload(self, incoming_file: Path) -> None:
        if incoming_file.parent == self.image_directory:
            self.update_image_data(incoming_file)
        elif incoming_file.parent == self.inferences_directory:
            self.update_inference_data(incoming_file.read_text())

    @run_on_ui_thread
    def update_image_data(self, incoming_file: Path) -> None:
        self.gui.views["streaming screen"].ids.stream_image.update_image_data(
            incoming_file
        )

    @run_on_ui_thread
    def update_inference_data(self, inference_data: str) -> None:
        self.gui.views["streaming screen"].ids.inference_field.text = inference_data

    async def streaming_rpc_start(self, roi: Optional[UnitROI] = None) -> None:
        instance_id = "backdoor-EA_Main"
        method = "StartUploadInferenceData"
        upload_url = f"http://{LOCAL_IP}:{self.upload_port}/"
        assert self.image_directory  # appease mypy
        assert self.inferences_directory  # appease mypy

        (h_offset, v_offset), (h_size, v_size) = pixel_roi_from_normals(roi)
        params = {
            "Mode": 1,
            "UploadMethod": "HttpStorage",
            "StorageName": upload_url,
            "StorageSubDirectoryPath": self.image_directory.name,
            "UploadMethodIR": "HttpStorage",
            "StorageNameIR": upload_url,
            "UploadInterval": 30,
            "StorageSubDirectoryPathIR": self.inferences_directory.name,
            "CropHOffset": h_offset,
            "CropVOffset": v_offset,
            "CropHSize": h_size,
            "CropVSize": v_size,
        }
        await self.mqtt_client.rpc(instance_id, method, json.dumps(params))

    async def streaming_rpc_stop(self) -> None:
        instance_id = "backdoor-EA_Main"
        method = "StopUploadInferenceData"
        await self.mqtt_client.rpc(instance_id, method, "{}")
