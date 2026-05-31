from kivy.properties import StringProperty, OptionProperty, BooleanProperty

from carbonkivy.uix.tab import CTab
from carbonkivy.behaviors import HoverBehavior

from View.components.RoundedBoxLayout import RoundedBoxLayout


class Service(HoverBehavior, RoundedBoxLayout):

    name = StringProperty()

    start_type = OptionProperty("START_NOT_STICKY", options=["START_NOT_STICKY", "START_STICKY", "START_REDELIVER_INTENT"])

    entrypoint = StringProperty()

    foreground = BooleanProperty()

    foreground_service_type = StringProperty()

    notification_title = StringProperty()

    notification_text = StringProperty()

    notification_icon = StringProperty("stat_notify_sync")

    def __init__(self, *args, **kwargs):
        super(Service, self).__init__(*args, **kwargs)


class Services(CTab):
    def __init__(self, *args, **kwargs):
        super(Services, self).__init__(*args, **kwargs)
