from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class BaseRewardComponent(ABC):
    """Base class for modular reward components."""

    name: str
    weight: float = 1.0
    enabled: bool = True

    @abstractmethod
    def calculate(self, state: dict, prev_state: dict) -> float:
        """Return the unweighted reward contribution for this component."""

    def reset(self) -> None:
        """Reset any episode-local state."""
        return None
