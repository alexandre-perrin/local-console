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
import logging
from typing import Any
from typing import Optional

import trio
from kivymd.app import MDApp
from local_console.core.camera.axis_mapping import UnitROI
from local_console.core.camera.state import CameraState
from local_console.core.camera.state import MessageType
from local_console.core.config import config_obj
from local_console.gui.device_manager import DeviceManager
from local_console.gui.utils.sync_async import AsyncFunc
from local_console.gui.utils.sync_async import run_on_ui_thread
from local_console.gui.utils.sync_async import SyncAsyncBridge
from trio import CancelScope
from trio import MemoryReceiveChannel


logger = logging.getLogger(__name__)


class Driver:

    def __init__(self, gui: type[MDApp]) -> None:
        self.gui = gui
        self.send_channel: trio.MemorySendChannel[MessageType] | None = None
        self.receive_channel: trio.MemoryReceiveChannel[MessageType] | None = None

        self.device_manager: Optional[DeviceManager] = None
        self.camera_state: Optional[CameraState] = None

        self.bridge = SyncAsyncBridge()

    @trio.lowlevel.disable_ki_protection
    async def main(self) -> None:
        async with trio.open_nursery() as nursery:
            try:
                nursery.start_soon(self.bridge.bridge_listener)
                self.send_channel, self.receive_channel = trio.open_memory_channel(0)
                channel_cs = CancelScope()
                async with self.send_channel, self.receive_channel:
                    nursery.start_soon(
                        self.show_messages, self.receive_channel.clone(), channel_cs
                    )
                    self.device_manager = DeviceManager(
                        self.send_channel,
                        nursery,
                        trio.lowlevel.current_trio_token(),
                    )
                    await self.device_manager.init_devices(
                        config_obj.get_device_configs()
                    )

                    await self.gui.async_run(async_lib="trio")

            except KeyboardInterrupt:
                logger.info("Cancelled per user request via keyboard")
            finally:
                channel_cs.cancel()
                self.bridge.close_task_queue()
                nursery.cancel_scope.cancel()

    def from_sync(self, async_fn: AsyncFunc, *args: Any) -> None:
        self.bridge.enqueue_task(async_fn, *args)

    async def show_messages(
        self, receive_channel: MemoryReceiveChannel[MessageType], cs: CancelScope
    ) -> None:
        with cs:
            async with receive_channel:
                async for value in receive_channel:
                    self.show_message_gui(value)

    @run_on_ui_thread
    def show_message_gui(self, msg: MessageType) -> None:
        type_ = msg[0]
        if type_ == "error":
            self.gui.display_error(msg[1], duration=30)
        else:
            raise NotImplementedError(f"Cannot show message of type '{type_}'")

    async def streaming_rpc_start(self, roi: Optional[UnitROI] = None) -> None:
        assert self.device_manager
        active = self.device_manager.get_active_device_state()
        await active.streaming_rpc_start(roi)

    async def streaming_rpc_stop(self) -> None:
        assert self.device_manager
        active = self.device_manager.get_active_device_state()
        await active.streaming_rpc_stop()

    async def send_app_config(self, config: str) -> None:
        assert self.device_manager
        active = self.device_manager.get_active_device_state()
        await active.send_app_config(config)

    def do_app_deployment(self) -> None:
        assert self.device_manager
        active = self.device_manager.get_active_device_state()
        self.from_sync(active.do_app_deployment)
