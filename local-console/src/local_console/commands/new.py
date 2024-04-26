import logging
import os
import shutil
from pathlib import Path
from typing import Annotated

import local_console.assets as assets
import typer

logger = logging.getLogger(__name__)

app = typer.Typer(
    help="Generates the necessary files to start a new project. It will be generated in the current directory. Can be used as template"
)


@app.callback(invoke_without_command=True)
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
