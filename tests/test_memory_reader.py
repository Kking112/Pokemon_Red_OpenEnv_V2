from __future__ import annotations

import json

from pokemon_red_env.memory.addresses import Addresses
from pokemon_red_env.memory.reader import MemoryReader


class _Mem:
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


def _make_reader(tmp_path, fake_pyboy):
    events = [
        {
            "id": "0xD747-0",
            "name": "got_pokedex",
            "description": "Got Pokedex",
            "address": 0xD747,
            "bit": 0,
        }
    ]
    maps = {"0": "Pallet Town", "1": "Viridian City"}
    curated = ["got_pokedex"]

    events_path = tmp_path / "events.json"
    maps_path = tmp_path / "maps.json"
    curated_path = tmp_path / "curated_events.json"

    events_path.write_text(json.dumps(events))
    maps_path.write_text(json.dumps(maps))
    curated_path.write_text(json.dumps(curated))

    return MemoryReader(
        pyboy=fake_pyboy,
        events_data_path=events_path,
        maps_data_path=maps_path,
        curated_events_path=curated_path,
    )


def test_memory_primitives(tmp_path):
    class _PB:
        def __init__(self):
            self.memory = _Mem()

    pb = _PB()
    pb.memory[0x100] = 0x12
    pb.memory[0x101] = 0x34
    pb.memory[0x102] = 0x56
    pb.memory[0x200] = 0x99

    reader = _make_reader(tmp_path, pb)
    assert reader.read_byte(0x200) == 0x99
    assert reader.read_word(0x100, big_endian=True) == 0x1234
    assert reader.read_word(0x100, big_endian=False) == 0x3412
    assert reader.read_custom(0x100, encoding="u24_be") == 0x123456


def test_read_bcd(tmp_path):
    class _PB:
        def __init__(self):
            self.memory = _Mem()

    pb = _PB()
    pb.memory[0x300] = 0x12
    pb.memory[0x301] = 0x34
    pb.memory[0x302] = 0x56
    reader = _make_reader(tmp_path, pb)
    assert reader.read_bcd(0x300, 3) == 123456


def test_extract_game_state_basic(tmp_path):
    class _PB:
        def __init__(self):
            self.memory = _Mem()

    pb = _PB()
    pb.memory[Addresses.PLAYER_X.address] = 3
    pb.memory[Addresses.PLAYER_Y.address] = 4
    pb.memory[Addresses.CURRENT_MAP.address] = 1
    pb.memory[Addresses.PARTY_COUNT.address] = 1

    base = Addresses.PARTY_BASES[0]
    pb.memory[base + Addresses.PARTY_OFFSET_LEVEL] = 7
    pb.memory[base + Addresses.PARTY_OFFSET_HP] = 0
    pb.memory[base + Addresses.PARTY_OFFSET_HP + 1] = 20
    pb.memory[base + Addresses.PARTY_OFFSET_MAX_HP] = 0
    pb.memory[base + Addresses.PARTY_OFFSET_MAX_HP + 1] = 40

    pb.memory[Addresses.OBTAINED_BADGES.address] = 0b00000011
    pb.memory[0xD747] = 0b00000001

    reader = _make_reader(tmp_path, pb)
    gs = reader.extract_game_state(step_count=2, total_reward=1.5, seen_coords_count=9)
    obs = gs.to_observation_dict()

    assert obs["player_x"] == 3
    assert obs["player_y"] == 4
    assert obs["map_name"] == "Viridian City"
    assert obs["party_count"] == 1
    assert obs["party_levels"] == [7]
    assert obs["badge_count"] == 2
    assert obs["event_flags"]["got_pokedex"] is True
