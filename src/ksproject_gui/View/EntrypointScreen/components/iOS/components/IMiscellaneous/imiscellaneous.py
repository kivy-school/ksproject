import re
from datetime import datetime
from zoneinfo import ZoneInfo


from kivy.metrics import dp

from carbonkivy.uix.tab import CTab
from carbonkivy.uix.boxlayout import CBoxLayout
from kivy.properties import StringProperty, ObjectProperty
from kivy.clock import Clock

from View.components.PreviewPane import PreviewPane


class IMiscellaneousLayout(CBoxLayout):

    color_picker = ObjectProperty()

    def __init__(self, *args, **kwargs):
        super(IMiscellaneousLayout, self).__init__(*args, **kwargs)

    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)

    def parse_hex_lenient(input_str, default="#FFFFFF"):
        if not isinstance(input_str, str):
            return default

        clean_str = re.sub(r'[^0-9a-fA-F]', '', input_str)
        
        if not clean_str:
            return default

        if len(clean_str) == 3:
            clean_str = "".join([char * 2 for char in clean_str])
        elif len(clean_str) >= 6:
            clean_str = clean_str[:6]
        else:
            clean_str = clean_str.ljust(6, '0')

        return f"#{clean_str.upper()}"


class IOSPane(PreviewPane):
    time = StringProperty()

    def __init__(self, *args, **kwargs):
        super(IOSPane, self).__init__(*args, **kwargs)
        Clock.schedule_interval(self.update_time, 1/60)

    def update_time(self, *args) -> None:
        self.time = datetime.now(ZoneInfo("UTC")).strftime("%H:%M")


class IMiscellaneous(CTab):

    def __init__(self, *args, **kwargs):
        super(IMiscellaneous, self).__init__(*args, **kwargs)