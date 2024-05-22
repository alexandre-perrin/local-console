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
import os
import shutil
from pathlib import Path
from typing import Annotated

import local_console.assets as assets
import typer

logger = logging.getLogger(__name__)

app = typer.Typer()


@app.command(
    help="Command for generating the boilerplate to start a new project. It will be generated in the current directory."
)
def new(
    project_name: Annotated[
        str,
        typer.Option(
            "--project_name",
            "-p",
            help="Name of the new project",
        ),
    ]
) -> None:
    project_path = Path(project_name)
    assets_path = assets.__path__[0]
    shutil.copytree(assets_path, project_path, dirs_exist_ok=True)
    shutil.move(
        project_path / "template", Path(os.path.join(project_path, project_path))
    )
