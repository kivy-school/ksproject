from __future__ import annotations

__all__ = ("RoundedBoxLayout",)

from kivy.uix.boxlayout import BoxLayout

from carbonkivy.behaviors import (
    AdaptiveBehavior,
    BackgroundColorBehaviorCircular,
    DeclarativeBehavior,
)


class RoundedBoxLayout(
    AdaptiveBehavior,
    BackgroundColorBehaviorCircular,
    BoxLayout,
    DeclarativeBehavior,
):
    pass
