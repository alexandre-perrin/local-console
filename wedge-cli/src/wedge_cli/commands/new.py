import logging
import shutil
from pathlib import Path

import wedge_cli.assets as assets

logger = logging.getLogger(__name__)


def new(project_name: str, **kwargs: dict) -> None:
    project_path = Path(project_name[0])
    assets_path = assets.__path__[0]
    shutil.copytree(assets_path, project_path, dirs_exist_ok=True)
    shutil.move(project_path / "template", project_path / project_path)
