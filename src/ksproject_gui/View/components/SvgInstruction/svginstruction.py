import os
from kivy.graphics import Rectangle
from kivy.graphics.texture import Texture
from kivy.resources import resource_find
from thorvg_cython import Engine, SwCanvas, Picture, Colorspace, Scene, Shape

class SvgInstruction(Rectangle):
    def __init__(self, **kwargs):
        self._svg_path = ""
        self._svg_color = [1.0, 1.0, 1.0, 1.0]
        self._svg_radius = 0.0
        self._svg_scale = 1.0

        self.engine = Engine()
        self.engine.init()

        super().__init__(**kwargs)

    @property
    def svg_path(self):
        return self._svg_path

    @svg_path.setter
    def svg_path(self, value):
        self._svg_path = resource_find(value)
        if value and self._svg_path and os.path.exists(self._svg_path):
            self._render_svg()

    @property
    def svg_color(self):
        return self._svg_color

    @svg_color.setter
    def svg_color(self, value):
        self._svg_color = value
        if self._svg_path and os.path.exists(self._svg_path):
            self._render_svg()

    @property
    def svg_radius(self):
        return self._svg_radius

    @svg_radius.setter
    def svg_radius(self, value):
        self._svg_radius = float(value)
        if self._svg_path and os.path.exists(self._svg_path):
            self._render_svg()

    @property
    def svg_scale(self):
        return self._svg_scale

    @svg_scale.setter
    def svg_scale(self, value):
        self._svg_scale = float(value)
        if self._svg_path and os.path.exists(self._svg_path):
            self._render_svg()

    def _render_svg(self):
        w, h = int(self.size[0]), int(self.size[1])
        if w <= 0 or h <= 0:
            w, h = 300, 300

        tvg_canvas = SwCanvas(w, h, int(Colorspace.ABGR8888))

        pic = Picture()
        pic.load(self._svg_path)

        draw_w = w * self._svg_scale
        draw_h = h * self._svg_scale
        offset_x = (w - draw_w) / 2.0
        offset_y = (h - draw_h) / 2.0

        pic.set_size(draw_w, draw_h)
        pic.translate(offset_x, offset_y)

        scene = Scene()
        scene.add(pic)

        r, g, b = [int(c * 255) for c in self._svg_color[:3]]
        a = int(self._svg_color[3] * 255)

        scene.add_effect_tint(r, g, b, r, g, b, 1.0)
        scene.set_opacity(a)

        if self._svg_radius > 0:
            clip_shape = Shape()
            clip_shape.append_rect(0, 0, w, h, self._svg_radius, self._svg_radius)
            scene.set_clip(clip_shape)

        tvg_canvas.add(scene)
        tvg_canvas.draw()
        tvg_canvas.sync()

        tex = Texture.create(size=(w, h), colorfmt="rgba", bufferfmt="ubyte")
        tex.flip_vertical()

        raw_buffer = bytes(tvg_canvas)

        tex.blit_buffer(raw_buffer, colorfmt="rgba", bufferfmt="ubyte")
        self.texture = tex