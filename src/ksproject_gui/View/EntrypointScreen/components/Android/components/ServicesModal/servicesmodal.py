import threading

from kivy.app import App
from kivy.clock import Clock

from carbonkivy.uix.modal import CModal
from carbonkivy.uix.dropdown import CDropdown


class StartTypeDropdown(CDropdown):

    def __init__(self, **kwargs) -> None:
        super(StartTypeDropdown, self).__init__(**kwargs)



class ServicesModal(CModal):

    def __init__(self, **kwargs) -> None:
        super(ServicesModal, self).__init__(**kwargs)
        self.app = App.get_running_app()

    def launch_start_type_dropdown(self, *args) -> None:
        self.dropdown = StartTypeDropdown(master=self.ids.start_type_dropdown_btn)
        self.dropdown.visibility = True
