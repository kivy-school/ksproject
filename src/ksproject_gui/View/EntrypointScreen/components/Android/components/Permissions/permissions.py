from kivy.properties import StringProperty
from kivy.clock import Clock

from carbonkivy.uix.tab import CTab
from carbonkivy.uix.boxlayout import CBoxLayout

from libs.datamodel import datamodel


class Permission(CBoxLayout):
    name = StringProperty()


class Permissions(CTab):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        Clock.schedule_once(self._setup_bindings)

    def _setup_bindings(self, dt=None):
        """
        Binds the UI to the datamodel so it automatically refreshes 
        if permissions are added or removed dynamically.
        """
        datamodel.bind(android_permissions=self.update_permissions_ui)

        self.update_permissions_ui(datamodel, datamodel.android_permissions)

    def update_permissions_ui(self, instance, permissions_list):
        """
        Clears the layout and repopulates it based on the datamodel list.
        """
        layout = self.ids.PermLayout

        layout.clear_widgets()

        for perm in (permissions_list or []):
            layout.add_widget(Permission(name=perm))

