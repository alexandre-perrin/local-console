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
from wedge_cli.gui.utils import run_on_ui_thread
from wedge_cli.gui.utils import SyncAsyncBridge
from wedge_cli.servers.broker import spawn_broker
from wedge_cli.servers.webserver import AsyncWebserver
from wedge_cli.utils.local_network import LOCAL_IP

logger = logging.getLogger(__name__)


class Driver:
    def __init__(self, gui: type[MDApp], nursery: trio.Nursery) -> None:
        self.gui = gui
        self.nursery = nursery

        self.mqtt_client = Agent()
        self.config = get_config()

        self.start_flags = {
            "mqtt": trio.Event(),
        }

        self.bridge = SyncAsyncBridge()

    async def main(self) -> None:
        self.nursery.start_soon(self.mqtt_setup)

        for flag in self.start_flags.values():
            await flag.wait()

        self.nursery.start_soon(self.gui_run)
        self.nursery.start_soon(self.bridge.bridge_listener)

    async def gui_run(self) -> None:
        await self.gui.async_run(async_lib="trio")
        self.bridge.enqueue_task(None)
        self.nursery.cancel_scope.cancel()

    async def mqtt_setup(self) -> None:
        async with (
            spawn_broker(self.config, self.nursery, False, "nicebroker"),
            self.mqtt_client.mqtt_scope(
                [Agent.TELEMETRY_TOPIC, Agent.RPC_RESPONSES_TOPIC]
            ),
        ):
            self.start_flags["mqtt"].set()

            assert self.mqtt_client.client  # appease mypy
            async for msg in self.mqtt_client.client.messages():
                payload = json.loads(msg.payload)
                logger.debug("Incoming on %s: %s", msg.topic, str(payload))

    def from_sync(self, async_fn: Callable, *args: Any) -> None:
        self.bridge.enqueue_task(async_fn, *args)
