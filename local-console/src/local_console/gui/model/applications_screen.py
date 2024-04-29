from local_console.commands.deploy import get_empty_deployment
from local_console.core.schemas.schemas import DeploymentManifest
from local_console.gui.model.base_model import BaseScreenModel


class ApplicationsScreenModel(BaseScreenModel):
    """
    Implements the logic of the
    :class:`~View.settings_screen.ApplicationsScreen.ApplicationsScreenView` class.
    """

    def __init__(self) -> None:
        self._manifest: DeploymentManifest = get_empty_deployment()
        self._deploy_status: dict[str, str] = {}

    @property
    def manifest(self) -> DeploymentManifest:
        return self._manifest

    @manifest.setter
    def manifest(self, value: DeploymentManifest) -> None:
        self._manifest = value
        self.notify_observers()

    @property
    def deploy_status(self) -> dict[str, str]:
        return self._deploy_status

    @deploy_status.setter
    def deploy_status(self, value: dict[str, str]) -> None:
        self._deploy_status = value
        self.notify_observers()
