from abc import ABC

from wedge_cli.gui.utils.observer import Observer

# The model implements the observer pattern. This means that the class must
# support adding, removing, and alerting observers. In this case, the model is
# completely independent of controllers and views. It is important that all
# registered observers implement a specific method that will be called by the
# model when they are notified (in this case, it is the `model_is_changed`
# method). For this, observers must be descendants of an abstract class,
# inheriting which, the `model_is_changed` method must be overridden.


class BaseScreenModel(ABC):
    """Implements a base class for model modules."""

    _observers: list[Observer] = []

    def add_observer(self, observer: Observer) -> None:
        self._observers.append(observer)

    def remove_observer(self, observer: Observer) -> None:
        self._observers.remove(observer)

    def notify_observers(self) -> None:
        """
        Method that will be called by the observer when the model data changes.
        """
        for observer in self._observers:
            observer.model_is_changed()
