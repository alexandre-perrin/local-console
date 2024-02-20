import logging
import os

import trio
import typer

logger = logging.getLogger(__name__)
app = typer.Typer(help="Command to start the GUI mode")


@app.callback(invoke_without_command=True)
def gui() -> None:
    os.environ["KIVY_LOG_MODE"] = "PYTHON"
    os.environ["KIVY_NO_ARGS"] = "1"
    os.environ["KIVY_NO_CONSOLELOG"] = "1"
    os.environ["KIVY_NO_FILELOG"] = "1"
    os.environ["KIVY_NO_CONFIG"] = "1"

    """
    This import must happen within this callback, as
    Kivy performs several initialization steps during
    imports.
    """
    from wedge_cli.gui.main import WedgeGUIApp

    trio.run(WedgeGUIApp().app_main)
