import os
from kivy.app import App
from kivy.uix.image import Image
from kivy.properties import StringProperty
from kivy.graphics.texture import Texture

from thorvg_cython import Engine, SwCanvas, Picture, Colorspace


class SvgWidget(Image):

    svg_path = StringProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.engine = Engine()
        self.engine.init()

        self._render_svg()

    def _render_svg(self):
        w, h = 300, 300
        tvg_canvas = SwCanvas(w, h, int(Colorspace.ABGR8888))

        pic = Picture()
        pic.load(self.svg_path)
        pic.set_size(w, h)

        tvg_canvas.add(pic)
        tvg_canvas.draw()
        tvg_canvas.sync()

        tex = Texture.create(size=(w, h), colorfmt="rgba", bufferfmt="ubyte")

        tex.flip_vertical()

        tex.blit_buffer(tvg_canvas, colorfmt="rgba", bufferfmt="ubyte")

        self.texture = tex

