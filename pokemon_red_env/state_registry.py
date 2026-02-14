from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DEFAULT_STATE_ALIASES: dict[str, str] = {
    "game_start": "home.state",
    "has_starter": "Bulbasaur.state",
    "has_pokedex": "has_pokedex.state",
}


@dataclass(frozen=True)
class ResolvedState:
    requested: str
    resolved_name: str
    path: Path


class StateRegistry:
    """Resolve user-facing aliases to concrete PyBoy state files."""

    def __init__(self, state_dir: Path, aliases: dict[str, str] | None = None):
        self.state_dir = state_dir
        self.aliases = dict(DEFAULT_STATE_ALIASES)
        if aliases:
            self.aliases.update(aliases)

    def available_states(self) -> list[str]:
        if not self.state_dir.exists():
            return []
        return sorted([p.name for p in self.state_dir.glob("*.state")])

    def resolve(self, requested: str | None, default_alias: str = "has_pokedex") -> ResolvedState:
        request = (requested or default_alias).strip()
        if not request:
            request = default_alias

        if request in self.aliases:
            file_name = self.aliases[request]
            path = self.state_dir / file_name
            if path.exists():
                return ResolvedState(requested=request, resolved_name=file_name, path=path)

        candidate = Path(request)
        if candidate.is_absolute() and candidate.exists():
            return ResolvedState(requested=request, resolved_name=candidate.name, path=candidate)

        if not candidate.suffix:
            candidate = candidate.with_suffix(".state")
        path = self.state_dir / candidate.name
        if path.exists():
            return ResolvedState(requested=request, resolved_name=path.name, path=path)

        available = ", ".join(self.available_states())
        alias_list = ", ".join(sorted(self.aliases.keys()))
        raise FileNotFoundError(
            f"Unknown init_state '{request}'. Aliases: [{alias_list}]. Available files: [{available}]"
        )
