from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class PartyMemberState:
    species: int = 0
    level: int = 0
    hp: int = 0
    max_hp: int = 0
    status: int = 0
    type1: int = 0
    type2: int = 0
    move1: int = 0
    exp: int = 0


@dataclass
class BattleState:
    in_battle: int = 0
    battle_outcome: int | None = None
    enemy_hp: int | None = None
    enemy_max_hp: int | None = None
    enemy_level: int | None = None
    enemy_species: int | None = None
    battle_mon_hp: int | None = None
    player_move_num: int | None = None


@dataclass
class ProgressState:
    badges: list[int] = field(default_factory=lambda: [0] * 8)
    badge_count: int = 0
    event_count: int = 0
    event_flags: dict[str, bool] = field(default_factory=dict)
    pokedex_owned_count: int = 0
    pokedex_seen_count: int = 0
    play_time_hours: int = 0


@dataclass
class GameState:
    player_x: int
    player_y: int
    map_id: int
    map_name: str
    map_tileset: int
    last_map: int
    walk_counter: int

    party_count: int
    party: list[PartyMemberState] = field(default_factory=list)
    party_hp: list[int] = field(default_factory=list)
    party_max_hp: list[int] = field(default_factory=list)
    party_levels: list[int] = field(default_factory=list)
    party_hp_fraction: float = 0.0
    level_sum: int = 0

    progression: ProgressState = field(default_factory=ProgressState)
    battle: BattleState = field(default_factory=BattleState)

    num_bag_items: int = 0
    num_box_items: int = 0
    player_money: int = 0

    text_box_id: int = 0
    current_menu_item: int = 0
    menu_watched_keys: int = 0
    top_menu_item_x: int = 0
    top_menu_item_y: int = 0
    letter_printing_delay_flags: int = 0

    seen_coords_count: int = 0
    step_count: int = 0
    total_reward: float = 0.0

    def to_observation_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "player_x": self.player_x,
            "player_y": self.player_y,
            "map_id": self.map_id,
            "map_name": self.map_name,
            "map_tileset": self.map_tileset,
            "last_map": self.last_map,
            "walk_counter": self.walk_counter,
            "party_count": self.party_count,
            "party_hp": list(self.party_hp),
            "party_max_hp": list(self.party_max_hp),
            "party_levels": list(self.party_levels),
            "party_hp_fraction": self.party_hp_fraction,
            "level_sum": self.level_sum,
            "badges": list(self.progression.badges),
            "badge_count": self.progression.badge_count,
            "event_count": self.progression.event_count,
            "event_flags": dict(self.progression.event_flags),
            "pokedex_owned_count": self.progression.pokedex_owned_count,
            "pokedex_seen_count": self.progression.pokedex_seen_count,
            "play_time_hours": self.progression.play_time_hours,
            "in_battle": self.battle.in_battle,
            "battle_outcome": self.battle.battle_outcome,
            "enemy_hp": self.battle.enemy_hp,
            "enemy_max_hp": self.battle.enemy_max_hp,
            "enemy_level": self.battle.enemy_level,
            "enemy_species": self.battle.enemy_species,
            "battle_mon_hp": self.battle.battle_mon_hp,
            "player_move_num": self.battle.player_move_num,
            "num_bag_items": self.num_bag_items,
            "num_box_items": self.num_box_items,
            "player_money": self.player_money,
            "text_box_id": self.text_box_id,
            "current_menu_item": self.current_menu_item,
            "menu_watched_keys": self.menu_watched_keys,
            "top_menu_item_x": self.top_menu_item_x,
            "top_menu_item_y": self.top_menu_item_y,
            "letter_printing_delay_flags": self.letter_printing_delay_flags,
            "seen_coords_count": self.seen_coords_count,
            "step_count": self.step_count,
            "total_reward": self.total_reward,
            "party": [asdict(member) for member in self.party],
        }
        return out
