from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

from hypothesis import given
from hypothesis import strategies as st
from typer.testing import CliRunner
from wedge_cli.commands.new import app

runner = CliRunner()


@given(
    st.text(min_size=1, max_size=5),
    st.lists(st.text(min_size=1, max_size=5), min_size=1),
)
def test_new_command(name: str, path_mock: str):
    assets_mock = Mock()
    assets_mock.__path__ = path_mock

    with (
        patch("wedge_cli.commands.new.assets", assets_mock),
        patch("wedge_cli.commands.new.shutil.copytree") as mock_copytree,
        patch("wedge_cli.commands.new.shutil.move") as mock_move,
    ):
        project_path = Path(name)
        result = runner.invoke(app, ["-p", name])
        mock_copytree.assert_called_once_with(
            path_mock[0], project_path, dirs_exist_ok=True
        )
        mock_move.assert_called_once_with(
            project_path / "template", project_path / project_path
        )
        assert result.exit_code == 0
