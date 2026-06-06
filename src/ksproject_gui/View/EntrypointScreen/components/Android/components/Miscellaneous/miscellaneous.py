from datetime import datetime
from zoneinfo import ZoneInfo

from carbonkivy.uix.tab import CTab
from kivy.properties import StringProperty, ObjectProperty
from kivy.clock import Clock

from View.components.PreviewPane import PreviewPane


class AndroidPane(PreviewPane):
    time = StringProperty()

    def __init__(self, *args, **kwargs):
        super(AndroidPane, self).__init__(*args, **kwargs)
        Clock.schedule_interval(self.update_time, 1/60)

    def update_time(self, *args) -> None:
        self.time = datetime.now(ZoneInfo("UTC")).strftime("%H:%M")


class Miscellaneous(CTab):

    def __init__(self, *args, **kwargs):
        super(Miscellaneous, self).__init__(*args, **kwargs)