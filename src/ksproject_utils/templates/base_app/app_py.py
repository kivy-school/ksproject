app_py = """\
import os
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window
from kivy.lang import Builder

class IntroScreen(BoxLayout):
    def on_button_click(self):
        # Update the subtitle text when the button is pressed
        self.ids.subtitle_label.text = "Explore the power of Python + KVLang!"
        self.ids.action_btn.text = "Ready to Build!"

class KivyIntroApp(App):
    def build(self):
        Window.clearcolor = [1, 1, 1, 1]
        # Using self.directory safely grabs the location where app.py lives
        Builder.load_file(os.path.join(self.directory, "app.kv"))
        return IntroScreen()
    
def main():
    app = KivyIntroApp()
    app.run()
"""