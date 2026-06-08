# The model implements the observer pattern. This means that the class must
# support adding, removing, and alerting observers. In this case, the model is
# completely independent of controllers and views. It is important that all
# registered observers implement a specific method that will be called by the
# model when they are notified (in this case, it is the `model_is_changed`
# method). For this, observers must be descendants of an abstract class,
# inheriting which, the `model_is_changed` method must be overridden.

from carbonkivy.uix.notification import CNotificationInline, CNotificationToast
from kivy.app import App
from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.properties import ListProperty


class BaseScreenModel(EventDispatcher):
    """Implements a base class for model modules."""

    _observers = ListProperty()


    def __init__(self, *args, **kwargs) -> None:
        super(BaseScreenModel, self).__init__(*args, **kwargs)
        self.app = App.get_running_app()
        self.notificationt = CNotificationToast()
        self.notificationl = CNotificationInline()

    def add_observer(self, observer: object) -> None:
        if not observer in self._observers:
            self._observers.append(observer)

    def remove_observer(self, observer: object) -> None:
        if observer in self._observers:
            self._observers.remove(observer)

    def notify_observers(self, name_screen: str) -> None:
        """
        Method that will be called by the observer when the model data changes.

        :param name_screen:
            name of the view for which the method should be called
            :meth:`model_is_changed`.
        """
        print("Notifying observers for screen:", name_screen)
        print("Observers:", self._observers)

        for observer in self._observers:
            if observer.name == name_screen:
                Clock.schedule_once(observer.model_is_changed)
                print("Observer notified:", observer.name)
                break
            else:
                print("Observer not notified:", observer.name)
                continue

    def notify(
        self,
        variant: str = "Inline",
        title: str = "",
        subtitle: str = "",
        status: str = "Info",
        time_caption_enabled: bool = True,
        *args
    ) -> None:
        if variant == "Inline":
            notification = self.notificationl
        else:
            notification = self.notificationt
        notification.title = title
        notification.subtitle = subtitle
        notification.status = status
        notification.time_caption_enabled = time_caption_enabled
        notification.open()
