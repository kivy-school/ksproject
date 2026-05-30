from kivy.utils import platform
from kivy.uix.image import AsyncImage
from kivy.uix.behaviors import ButtonBehavior
from kivy.properties import StringProperty

from View.base_screen import BaseScreenView

from carbonkivy.behaviors import SelectableBehavior, BackgroundColorBehaviorRectangular
from carbonkivy.uix.boxlayout import CBoxLayout


class SelectionItem(SelectableBehavior, ButtonBehavior, CBoxLayout):
    source = StringProperty()


class EntrypointScreenView(BaseScreenView):

    def __init__(self, *args, **kwargs) -> None:
        super(EntrypointScreenView, self).__init__(*args, **kwargs)
