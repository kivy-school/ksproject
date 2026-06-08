from carbonkivy.uix.anchorlayout import CAnchorLayout
from carbonkivy.uix.modal import CModal
from kivy.core.window import Window
from kivy.properties import StringProperty


class WindowPreview(CModal):

    source = StringProperty(None, allownone=True)

    def __init__(self, **kwargs) -> None:
        super(WindowPreview, self).__init__(**kwargs)

    def dismiss(self):
        try:
            Window.remove_widget(self)
        except Exception as e:
            return


class ImagePreview(CAnchorLayout):

    source = StringProperty(None, allownone=True)

    def __init__(self, **kwargs) -> None:
        super(ImagePreview, self).__init__(**kwargs)
        self.window_preview = WindowPreview()

    def preview(self, *args):
        self.window_preview.source = self.source
        try:
            Window.add_widget(self.window_preview)
        except Exception as e:
            return
