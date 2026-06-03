import threading

from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.properties import ListProperty, StringProperty

from carbonkivy.uix.modal import CModal
from carbonkivy.uix.boxlayout import CBoxLayout

from libs.fetch_permissions import AndroidPermissionAPI
from libs.datamodel import datamodel

class NewPermission(CBoxLayout):
    name = StringProperty()


class PermissionsModal(CModal):
    available_perms = ListProperty()

    def __init__(self, *args, **kwargs) -> None:
        super(PermissionsModal, self).__init__(*args, **kwargs)
        self.app = App.get_running_app()
        self.api = AndroidPermissionAPI()
        # datamodel.bind(android_permissions=lambda e: self.ids.rcv.refresh_from_viewport())

        self._all_raw_perms = []

    def fetch(self, *args) -> None:
        self.app.loading_state(True, master=self)
        threading.Thread(target=self._fetch_in_background, daemon=True).start()

    def _fetch_in_background(self):
        raw_permissions = self.api.get_permissions()
        self._update_ui_data(raw_permissions)

    @mainthread
    def _update_ui_data(self, raw_permissions):
        self._all_raw_perms = raw_permissions

        self.available_perms = [{"name": perm} for perm in raw_permissions]
        self.filter_perms(self.ids.filter_input.text)
        self.app.loading_state(False, master=self)

    def filter_perms(self, text: str) -> None:
        """Filters the recycleview based on the text input."""
        if not self._all_raw_perms:
            return

        search_query = text.strip().upper()

        filtered_list = [
            perm for perm in self._all_raw_perms if search_query in perm.upper()
        ]

        self.available_perms = [{"name": perm} for perm in filtered_list]
