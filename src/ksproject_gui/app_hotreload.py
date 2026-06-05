import os
import registers
import threading
import ssl
import importlib

from kivy.resources import resource_add_path

resource_add_path(os.path.dirname(__file__))

# ssl.create_default_context = ssl._create_unverified_context


import time
import weakref
import webbrowser

from carbonkivy.app import CarbonApp
from carbonkivy.devtools import LiveApp
from carbonkivy.uix.screen import CScreen
from carbonkivy.uix.screenmanager import CScreenManager
from carbonkivy.uix.notification import CNotificationToast
from kivy.clock import Clock, mainthread
from kivy.core.window import Window
from kivy.logger import Logger
from kivy.utils import platform


from View.base_screen import LoadingLayout
from Model.application_layer_model import ApplicationLayerModel

Clock.max_iteration = 60

Window.maximize()

Window.minimum_width = 1000
Window.minimum_height = 500


def set_softinput(*args) -> None:
    Window.keyboard_anim_args = {"d": 0.2, "t": "in_out_expo"}
    Window.softinput_mode = "below_target"


Window.on_restore(Clock.schedule_once(set_softinput, 0.1))


class UI(CScreenManager):
    def __init__(self, *args, **kwargs):
        super(UI, self).__init__(*args, **kwargs)


class MainScreen(CScreen):

    def __init__(self, **kwargs) -> None:
        super(MainScreen, self).__init__(**kwargs)


class KsprojectApp(LiveApp, CarbonApp):

    def __init__(self, *args, **kwargs):
        self.theme = "Gray100"
        self.DEBUG = True
        super(KsprojectApp, self).__init__(*args, **kwargs)
        # self.load_all_kv_files(os.path.join(self.directory, "View"))
        self.loading_layout = LoadingLayout()
        self.notification = CNotificationToast()
        self.view_model = ApplicationLayerModel()
        self._running = False

    def build_app(self) -> UI:
        self.manager_screens = UI()
        self.main_screen = MainScreen(name="main screen")
        self.main_screen.ids.main_layout.add_widget(self.manager_screens)
        self.generate_application_screens()
        return self.main_screen

    def on_stop(self, *args) -> None:
        self._running = False

    def generate_application_screens(self, *args) -> None:
        # adds different screen widgets to the screen manager
        import View.screens

        importlib.reload(View.screens)

        screens = View.screens.screens

        for i, name_screen in enumerate(screens.keys()):
            model = screens[name_screen]["model"]()
            view = screens[name_screen]["object"](view_model=model)
            model.add_observer(view)
            view.manager_screens = self.manager_screens
            view.name = name_screen

            self.manager_screens.add_widget(view)

    def on_start(self):
        self._running = True

        self.loading_state(False)

    def referrer(self, destination: str = None) -> None:
        if self.manager_screens.current != destination:
            self.manager_screens.current = destination
        # try:
        #         # if not destination in self.manager_screens.upstream_views:
        #         #     self.manager_screens.switch(destination)
        #         # else:
        #         #     self.manager_screens.current = destination
        # except Exception as e:
        #     print(e)

    def notify(
        self,
        title: str = "",
        subtitle: str = "",
        status: str = "Info",
        time_caption_enabled: bool = True,
        *args,
    ) -> None:
        self.notification.title = title
        self.notification.subtitle = subtitle
        self.notification.status = status
        self.notification.time_caption_enabled = time_caption_enabled
        self.notification.open()

    def debugger(self, *args) -> None:
        pass

    def web_open(self, url: str) -> None:
        webbrowser.open_new_tab(url)

    @mainthread
    def loading_state(
        self, state: bool = False, master: object = Window, *args
    ) -> None:
        try:
            if state and not (
                hasattr(master, "loading_layout") and master.loading_layout != None
            ):
                master.loading_layout = LoadingLayout()
                _layout_ref = weakref.ref(master.loading_layout)
                master.add_widget(master.loading_layout)
                _layout_ref = None
                print("Loading")
            else:
                master.remove_widget(master.loading_layout)
                master.loading_layout = None
        except Exception as e:
            Logger.error(f"Loading State Error {e}")
            return None


def main(*args) -> None:
    app = KsprojectApp()
    app.run()


if __name__ == "__main__":
    main()
