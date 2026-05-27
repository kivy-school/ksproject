"""Minimal Kivy app used as a test fixture.

Prints a known marker on startup so e2e tests can assert it in logs.
"""
from kivy.app import App
from kivy.uix.label import Label


KSPROJECT_TEST_MARKER = "KSPROJECT_TEST_MARKER_OK"


class MinimalApp(App):
    def build(self) -> Label:
        print(KSPROJECT_TEST_MARKER, flush=True)
        return Label(text="Minimal")


def main() -> None:
    MinimalApp().run()


if __name__ == "__main__":
    main()
