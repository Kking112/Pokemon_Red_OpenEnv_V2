from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pyboy.utils import WindowEvent


@dataclass(frozen=True)
class ActionBinding:
    """Static action mapping for environment step execution."""

    name: str
    press_event: Optional[WindowEvent]
    release_event: Optional[WindowEvent]
    is_noop: bool = False


def build_action_bindings(include_select: bool, include_noop: bool = True) -> list[ActionBinding]:
    """Build the discrete action list.

    Ordering contract:
    1. Base gameplay actions
    2. Optional SELECT
    3. Optional NOOP (always appended as final index)
    """

    bindings: list[ActionBinding] = [
        ActionBinding(
            name="up",
            press_event=WindowEvent.PRESS_ARROW_UP,
            release_event=WindowEvent.RELEASE_ARROW_UP,
        ),
        ActionBinding(
            name="down",
            press_event=WindowEvent.PRESS_ARROW_DOWN,
            release_event=WindowEvent.RELEASE_ARROW_DOWN,
        ),
        ActionBinding(
            name="left",
            press_event=WindowEvent.PRESS_ARROW_LEFT,
            release_event=WindowEvent.RELEASE_ARROW_LEFT,
        ),
        ActionBinding(
            name="right",
            press_event=WindowEvent.PRESS_ARROW_RIGHT,
            release_event=WindowEvent.RELEASE_ARROW_RIGHT,
        ),
        ActionBinding(
            name="a",
            press_event=WindowEvent.PRESS_BUTTON_A,
            release_event=WindowEvent.RELEASE_BUTTON_A,
        ),
        ActionBinding(
            name="b",
            press_event=WindowEvent.PRESS_BUTTON_B,
            release_event=WindowEvent.RELEASE_BUTTON_B,
        ),
        ActionBinding(
            name="start",
            press_event=WindowEvent.PRESS_BUTTON_START,
            release_event=WindowEvent.RELEASE_BUTTON_START,
        ),
    ]

    if include_select:
        bindings.append(
            ActionBinding(
                name="select",
                press_event=WindowEvent.PRESS_BUTTON_SELECT,
                release_event=WindowEvent.RELEASE_BUTTON_SELECT,
            )
        )

    if include_noop:
        bindings.append(
            ActionBinding(name="noop", press_event=None, release_event=None, is_noop=True)
        )

    return bindings
