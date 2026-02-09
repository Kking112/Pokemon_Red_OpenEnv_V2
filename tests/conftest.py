from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pytest


class FakeMemory:
    def __init__(self, size: int = 0x10000):
        self.buf = bytearray(size)

    def __getitem__(self, key):
        if isinstance(key, slice):
            start = 0 if key.start is None else key.start
            stop = len(self.buf) if key.stop is None else key.stop
            step = 1 if key.step is None else key.step
            return self.buf[start:stop:step]
        return self.buf[key]

    def __setitem__(self, key, value):
        if isinstance(key, slice):
            self.buf[key] = value
        else:
            self.buf[key] = int(value) & 0xFF


@dataclass
class FakeScreen:
    ndarray: np.ndarray = field(
        default_factory=lambda: np.zeros((144, 160, 4), dtype=np.uint8)
    )


class FakePyBoy:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.memory = FakeMemory()
        self.screen = FakeScreen()
        self.inputs = []
        self.ticks = []
        self.loaded_states = []

    def set_emulation_speed(self, speed: int):
        self.speed = speed

    def send_input(self, event, delay: int = 0):
        self.inputs.append((event, delay))

    def tick(self, count: int = 1, render: bool = True):
        self.ticks.append((count, render))
        return True

    def load_state(self, file_obj):
        self.loaded_states.append(file_obj.read())

    def stop(self, save: bool = False):
        self.stopped = save


@pytest.fixture()
def temp_state_dir(tmp_path: Path) -> Path:
    for name in ["home.state", "Bulbasaur.state", "has_pokedex.state"]:
        (tmp_path / name).write_bytes(b"state")
    return tmp_path


@pytest.fixture()
def fake_pyboy_cls():
    return FakePyBoy
