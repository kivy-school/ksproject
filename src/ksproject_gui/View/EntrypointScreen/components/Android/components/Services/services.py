from kivy.properties import StringProperty, OptionProperty, BooleanProperty
from kivy.clock import Clock

from carbonkivy.uix.tab import CTab
from carbonkivy.behaviors import HoverBehavior

from View.components.RoundedBoxLayout import RoundedBoxLayout
from ..ServicesModal import ServicesModal

from libs.datamodel import datamodel


class Service(HoverBehavior, RoundedBoxLayout):
    name = StringProperty()

    start_type = OptionProperty(
        "START_NOT_STICKY",
        options=["START_NOT_STICKY", "START_STICKY", "START_REDELIVER_INTENT"],
    )

    entrypoint = StringProperty()

    foreground = BooleanProperty(False)

    foreground_service_type = StringProperty()

    notification_title = StringProperty()

    notification_text = StringProperty()

    notification_icon = StringProperty("stat_notify_sync")

    def __init__(self, *args, **kwargs):
        super(Service, self).__init__(*args, **kwargs)


class Services(CTab):
    def __init__(self, *args, **kwargs):
        super(Services, self).__init__(*args, **kwargs)
        Clock.schedule_once(self._setup_bindings)

    def _setup_bindings(self, dt=None):
        """
        Binds the UI to the datamodel so it automatically refreshes
        if services are added or removed dynamically.
        """
        datamodel.bind(android_services=self.update_services_ui)

        self.update_services_ui(datamodel, datamodel.android_services)

    def update_services_ui(self, instance, services_list):
        """
        Clears the layout and repopulates it based on the datamodel list.
        """
        layout = self.ids.ServiceLayout
        layout.clear_widgets()

        for srv in services_list or []:
            widget = Service(
                name=srv.name,
                entrypoint=srv.entrypoint,
                foreground=srv.foreground,
                foreground_service_type=srv.foreground_service_type or "",
            )
            layout.add_widget(widget)

    def launch_modal(self, *args) -> None:
        self.modal = ServicesModal()
        self.modal.open()
