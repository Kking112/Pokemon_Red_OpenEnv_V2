from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pyboy import PyBoy

from .addresses import Addresses
from .game_state import BattleState, GameState, PartyMemberState, ProgressState


class MemoryReader:
    """Thin wrapper over PyBoy RAM reads with Pokemon Red helpers."""

    def __init__(
        self,
        pyboy: PyBoy,
        events_data_path: Path,
        maps_data_path: Path,
        curated_events_path: Path | None = None,
        event_flags_mode: str = "curated",
        event_flags_max_count: int = 1024,
    ) -> None:
        self.pyboy = pyboy
        self.event_flags_mode = event_flags_mode
        self.event_flags_max_count = event_flags_max_count

        self._events_by_id: dict[str, dict[str, Any]] = {}
        self._events_by_name: dict[str, dict[str, Any]] = {}
        self._map_names: dict[int, str] = {}
        self._curated_event_names: list[str] = []

        self._load_event_table(events_data_path)
        self._load_map_table(maps_data_path)
        if curated_events_path is not None:
            self._load_curated_events(curated_events_path)

    def _load_event_table(self, path: Path) -> None:
        if not path.exists():
            return
        raw = json.loads(path.read_text())
        if not isinstance(raw, list):
            return
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            event_id = str(entry.get("id", "")).strip()
            event_name = str(entry.get("name", "")).strip()
            if not event_id:
                continue
            self._events_by_id[event_id] = entry
            if event_name:
                self._events_by_name[event_name] = entry

    def _load_map_table(self, path: Path) -> None:
        if not path.exists():
            return
        raw = json.loads(path.read_text())
        if not isinstance(raw, dict):
            return
        for map_id, name in raw.items():
            try:
                idx = int(map_id)
            except (TypeError, ValueError):
                continue
            self._map_names[idx] = str(name)

    def _load_curated_events(self, path: Path) -> None:
        if not path.exists():
            return
        raw = json.loads(path.read_text())
        if isinstance(raw, list):
            self._curated_event_names = [str(item) for item in raw if isinstance(item, str)]

    def read_byte(self, address: int) -> int:
        return int(self.pyboy.memory[address])

    def read_word(self, address: int, big_endian: bool = True) -> int:
        a = self.read_byte(address)
        b = self.read_byte(address + 1)
        if big_endian:
            return (a << 8) | b
        return (b << 8) | a

    def read_bytes(self, address: int, length: int) -> bytes:
        return bytes(self.read_byte(address + i) for i in range(length))

    def read_bcd(self, address: int, length: int) -> int:
        value = 0
        for byte in self.read_bytes(address, length):
            hi = (byte >> 4) & 0xF
            lo = byte & 0xF
            value = value * 100 + hi * 10 + lo
        return value

    def read_bit(self, address: int, bit: int) -> bool:
        if bit < 0 or bit > 7:
            raise ValueError("bit must be in [0, 7]")
        return bool(self.read_byte(address) & (1 << bit))

    def read_event_flag(self, flag_name: str) -> bool:
        entry = self._events_by_name.get(flag_name) or self._events_by_id.get(flag_name)
        if entry is None:
            raise KeyError(f"Unknown event flag '{flag_name}'")
        address = int(entry["address"])
        bit = int(entry["bit"])
        return self.read_bit(address, bit)

    def read_custom(self, address: int, width: int = 1, encoding: str = "u8") -> Any:
        if width <= 0:
            raise ValueError("width must be positive")
        if encoding == "u8":
            return self.read_byte(address)
        if encoding == "u16_be":
            return self.read_word(address, big_endian=True)
        if encoding == "u16_le":
            return self.read_word(address, big_endian=False)
        if encoding == "u24_be":
            data = self.read_bytes(address, 3)
            return (data[0] << 16) | (data[1] << 8) | data[2]
        if encoding == "bcd":
            return self.read_bcd(address, width)
        if encoding == "bytes":
            return self.read_bytes(address, width)
        raise ValueError(f"Unsupported encoding '{encoding}'")

    def _decode_badges(self, bitmask: int) -> list[int]:
        return [1 if (bitmask & (1 << i)) else 0 for i in range(8)]

    def _extract_event_flags(self, mode: str, max_count: int) -> dict[str, bool]:
        if mode == "none":
            return {}

        if mode == "curated":
            names = self._curated_event_names
            if not names:
                names = sorted(self._events_by_name.keys())[: min(max_count, 32)]
            result: dict[str, bool] = {}
            for name in names[:max_count]:
                entry = self._events_by_name.get(name)
                if entry is None:
                    continue
                result[name] = self.read_bit(int(entry["address"]), int(entry["bit"]))
            return result

        # mode == all
        result: dict[str, bool] = {}
        entries = sorted(
            self._events_by_id.values(),
            key=lambda e: (int(e["address"]), int(e["bit"]), str(e.get("name", ""))),
        )
        for entry in entries[:max_count]:
            key = str(entry.get("name") or entry.get("id"))
            result[key] = self.read_bit(int(entry["address"]), int(entry["bit"]))
        return result

    def _pokedex_count(self, start: int, length: int) -> int:
        bits = 0
        for byte in self.read_bytes(start, length):
            bits += int(byte).bit_count()
        return bits

    def _event_count(self) -> int:
        start = Addresses.EVENT_FLAGS_START.address
        end = Addresses.EVENT_FLAGS_END_INCLUSIVE
        total = 0
        for addr in range(start, end + 1):
            total += self.read_byte(addr).bit_count()
        return total

    def _extract_party_member(self, slot: int) -> PartyMemberState:
        base = Addresses.PARTY_BASES[slot]
        hp = self.read_word(base + Addresses.PARTY_OFFSET_HP, big_endian=True)
        max_hp = self.read_word(base + Addresses.PARTY_OFFSET_MAX_HP, big_endian=True)
        exp_bytes = self.read_bytes(base + Addresses.PARTY_OFFSET_EXP, 3)
        exp = (exp_bytes[0] << 16) | (exp_bytes[1] << 8) | exp_bytes[2]
        return PartyMemberState(
            species=self.read_byte(base + Addresses.PARTY_OFFSET_SPECIES),
            level=self.read_byte(base + Addresses.PARTY_OFFSET_LEVEL),
            hp=hp,
            max_hp=max_hp,
            status=self.read_byte(base + Addresses.PARTY_OFFSET_STATUS),
            type1=self.read_byte(base + Addresses.PARTY_OFFSET_TYPE1),
            type2=self.read_byte(base + Addresses.PARTY_OFFSET_TYPE2),
            move1=self.read_byte(base + Addresses.PARTY_OFFSET_MOVE1),
            exp=exp,
        )

    def extract_game_state(
        self,
        *,
        step_count: int,
        total_reward: float,
        seen_coords_count: int,
        event_flags_mode: str | None = None,
        event_flags_max_count: int | None = None,
    ) -> GameState:
        mode = event_flags_mode or self.event_flags_mode
        max_count = (
            self.event_flags_max_count if event_flags_max_count is None else event_flags_max_count
        )

        player_x = self.read_byte(Addresses.PLAYER_X.address)
        player_y = self.read_byte(Addresses.PLAYER_Y.address)
        map_id = self.read_byte(Addresses.CURRENT_MAP.address)
        map_name = self._map_names.get(map_id, f"Map {map_id}")

        party_count = max(0, min(6, self.read_byte(Addresses.PARTY_COUNT.address)))
        party = [self._extract_party_member(i) for i in range(party_count)]

        party_hp = [member.hp for member in party]
        party_max_hp = [member.max_hp for member in party]
        party_levels = [member.level for member in party]
        hp_total = sum(party_hp)
        max_hp_total = max(sum(party_max_hp), 1)

        badges_bitmask = self.read_byte(Addresses.OBTAINED_BADGES.address)
        badges = self._decode_badges(badges_bitmask)

        event_flags = self._extract_event_flags(mode=mode, max_count=max_count)

        in_battle = self.read_byte(Addresses.IS_IN_BATTLE.address)
        battle = BattleState(
            in_battle=in_battle,
            battle_outcome=self.read_byte(Addresses.BATTLE_RESULT.address) if in_battle else None,
            enemy_hp=self.read_word(Addresses.ENEMY_MON_HP.address, big_endian=True)
            if in_battle
            else None,
            enemy_max_hp=self.read_word(Addresses.ENEMY_MON_MAX_HP.address, big_endian=True)
            if in_battle
            else None,
            enemy_level=self.read_byte(Addresses.ENEMY_MON_LEVEL.address) if in_battle else None,
            enemy_species=self.read_byte(Addresses.ENEMY_MON_SPECIES.address)
            if in_battle
            else None,
            battle_mon_hp=self.read_word(Addresses.BATTLE_MON_HP.address, big_endian=True)
            if in_battle
            else None,
            player_move_num=self.read_byte(Addresses.PLAYER_MOVE_NUM.address)
            if in_battle
            else None,
        )

        progression = ProgressState(
            badges=badges,
            badge_count=sum(badges),
            event_count=self._event_count(),
            event_flags=event_flags,
            pokedex_owned_count=self._pokedex_count(
                Addresses.POKEDEX_OWNED.address, Addresses.POKEDEX_OWNED.width
            ),
            pokedex_seen_count=self._pokedex_count(
                Addresses.POKEDEX_SEEN.address, Addresses.POKEDEX_SEEN.width
            ),
            play_time_hours=self.read_byte(Addresses.PLAY_TIME_HOURS.address),
        )

        return GameState(
            player_x=player_x,
            player_y=player_y,
            map_id=map_id,
            map_name=map_name,
            map_tileset=self.read_byte(Addresses.CURRENT_MAP_TILESET.address),
            last_map=self.read_byte(Addresses.LAST_MAP.address),
            walk_counter=self.read_byte(Addresses.WALK_COUNTER.address),
            party_count=party_count,
            party=party,
            party_hp=party_hp,
            party_max_hp=party_max_hp,
            party_levels=party_levels,
            party_hp_fraction=hp_total / max_hp_total,
            level_sum=sum(party_levels),
            progression=progression,
            battle=battle,
            num_bag_items=self.read_byte(Addresses.NUM_BAG_ITEMS.address),
            num_box_items=self.read_byte(Addresses.NUM_BOX_ITEMS.address),
            player_money=self.read_bcd(
                Addresses.PLAYER_MONEY.address,
                Addresses.PLAYER_MONEY.width,
            ),
            text_box_id=self.read_byte(Addresses.TEXT_BOX_ID.address),
            current_menu_item=self.read_byte(Addresses.CURRENT_MENU_ITEM.address),
            menu_watched_keys=self.read_byte(Addresses.MENU_WATCHED_KEYS.address),
            top_menu_item_x=self.read_byte(Addresses.TOP_MENU_ITEM_X.address),
            top_menu_item_y=self.read_byte(Addresses.TOP_MENU_ITEM_Y.address),
            letter_printing_delay_flags=self.read_byte(
                Addresses.LETTER_PRINTING_DELAY_FLAGS.address
            ),
            seen_coords_count=seen_coords_count,
            step_count=step_count,
            total_reward=float(total_reward),
        )
