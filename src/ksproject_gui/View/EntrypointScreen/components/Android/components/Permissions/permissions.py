from kivy.properties import StringProperty

from carbonkivy.uix.tab import CTab

from carbonkivy.uix.boxlayout import CBoxLayout

class Permission(CBoxLayout):

    name = StringProperty()


class Permissions(CTab):

    def __init__(self, *args, **kwargs):
        super(Permissions, self).__init__(*args, **kwargs)
