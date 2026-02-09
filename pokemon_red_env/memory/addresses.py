from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AddressSpec:
    """Metadata for a known RAM location."""

    name: str
    address: int
    width: int = 1
    encoding: str = "u8"
    description: str = ""


class Addresses:
    """Canonical Pokemon Red (US) RAM addresses used by the environment."""

    # Player position and map
    PLAYER_Y = AddressSpec("wYCoord", 0xD361, 1, "u8", "Player Y coordinate")
    PLAYER_X = AddressSpec("wXCoord", 0xD362, 1, "u8", "Player X coordinate")
    CURRENT_MAP = AddressSpec("wCurMap", 0xD35E, 1, "u8", "Current map id")
    CURRENT_MAP_TILESET = AddressSpec(
        "wCurMapTileset", 0xD367, 1, "u8", "Current map tileset id"
    )
    WALK_COUNTER = AddressSpec(
        "wWalkCounter", 0xCFC5, 1, "u8", "Walk animation counter"
    )
    LAST_MAP = AddressSpec("wLastMap", 0xD365, 1, "u8", "Previous map id")

    # Party
    PARTY_COUNT = AddressSpec("wPartyCount", 0xD163, 1, "u8", "Party size (0-6)")
    PARTY_MON1_BASE = AddressSpec("wPartyMon1", 0xD16B, 0x2C, "struct", "Party mon #1 base")
    PARTY_MON2_BASE = AddressSpec("wPartyMon2", 0xD197, 0x2C, "struct", "Party mon #2 base")
    PARTY_MON3_BASE = AddressSpec("wPartyMon3", 0xD1C3, 0x2C, "struct", "Party mon #3 base")
    PARTY_MON4_BASE = AddressSpec("wPartyMon4", 0xD1EF, 0x2C, "struct", "Party mon #4 base")
    PARTY_MON5_BASE = AddressSpec("wPartyMon5", 0xD21B, 0x2C, "struct", "Party mon #5 base")
    PARTY_MON6_BASE = AddressSpec("wPartyMon6", 0xD247, 0x2C, "struct", "Party mon #6 base")

    # Party structure offsets from each PARTY_MONn base
    PARTY_STRUCT_SIZE = 0x2C
    PARTY_OFFSET_SPECIES = 0x00
    PARTY_OFFSET_HP = 0x01
    PARTY_OFFSET_STATUS = 0x04
    PARTY_OFFSET_TYPE1 = 0x05
    PARTY_OFFSET_TYPE2 = 0x06
    PARTY_OFFSET_MOVE1 = 0x08
    PARTY_OFFSET_EXP = 0x0E
    PARTY_OFFSET_LEVEL = 0x21
    PARTY_OFFSET_MAX_HP = 0x22

    # Progression
    OBTAINED_BADGES = AddressSpec(
        "wObtainedBadges", 0xD356, 1, "bitmask", "Gym badge bitmask"
    )
    POKEDEX_OWNED = AddressSpec("wPokedexOwned", 0xD2F7, 19, "bitmask", "Owned Pokemon bits")
    POKEDEX_SEEN = AddressSpec("wPokedexSeen", 0xD30A, 19, "bitmask", "Seen Pokemon bits")
    PLAY_TIME_HOURS = AddressSpec(
        "wPlayTimeHours", 0xDA41, 1, "u8", "In-game play time hours"
    )

    # Battle
    IS_IN_BATTLE = AddressSpec("wIsInBattle", 0xD057, 1, "u8", "0=overworld,1=wild,2=trainer")
    BATTLE_RESULT = AddressSpec("wBattleResult", 0xCF0B, 1, "u8", "Battle result code")
    ENEMY_MON_HP = AddressSpec("wEnemyMonHP", 0xCFE6, 2, "u16_be", "Enemy current HP")
    ENEMY_MON_MAX_HP = AddressSpec(
        "wEnemyMonMaxHP", 0xCFF4, 2, "u16_be", "Enemy max HP"
    )
    ENEMY_MON_LEVEL = AddressSpec("wEnemyMonLevel", 0xCFF3, 1, "u8", "Enemy level")
    ENEMY_MON_SPECIES = AddressSpec("wEnemyMonSpecies", 0xCFE5, 1, "u8", "Enemy species")
    BATTLE_MON_HP = AddressSpec("wBattleMonHP", 0xD015, 2, "u16_be", "Active ally HP")
    PLAYER_MOVE_NUM = AddressSpec("wPlayerMoveNum", 0xCFD2, 1, "u8", "Selected move slot")

    # Items / money
    NUM_BAG_ITEMS = AddressSpec("wNumBagItems", 0xD31D, 1, "u8", "Bag item count")
    PLAYER_MONEY = AddressSpec("wPlayerMoney", 0xD347, 3, "bcd", "Money in BCD")
    NUM_BOX_ITEMS = AddressSpec("wNumBoxItems", 0xD53A, 1, "u8", "PC box item count")

    # Text/menu
    TEXT_BOX_ID = AddressSpec("wTextBoxID", 0xD125, 1, "u8", "Current text box id")
    CURRENT_MENU_ITEM = AddressSpec("wCurrentMenuItem", 0xCC26, 1, "u8", "Menu cursor index")
    MENU_WATCHED_KEYS = AddressSpec("wMenuWatchedKeys", 0xCC29, 1, "u8", "Menu watched keys")
    TOP_MENU_ITEM_Y = AddressSpec("wTopMenuItemY", 0xCC24, 1, "u8", "Top menu cursor Y")
    TOP_MENU_ITEM_X = AddressSpec("wTopMenuItemX", 0xCC25, 1, "u8", "Top menu cursor X")
    LETTER_PRINTING_DELAY_FLAGS = AddressSpec(
        "wLetterPrintingDelayFlags", 0xD358, 1, "u8", "Text speed flags"
    )

    # Event flags range (derived from source events table)
    EVENT_FLAGS_START = AddressSpec("wEventFlags", 0xD747, 1, "u8", "Event flag start")
    EVENT_FLAGS_END_INCLUSIVE = 0xD886

    PARTY_BASES = [
        PARTY_MON1_BASE.address,
        PARTY_MON2_BASE.address,
        PARTY_MON3_BASE.address,
        PARTY_MON4_BASE.address,
        PARTY_MON5_BASE.address,
        PARTY_MON6_BASE.address,
    ]


PLAYER_X = Addresses.PLAYER_X.address
PLAYER_Y = Addresses.PLAYER_Y.address
PARTY_MON_1_HP = Addresses.PARTY_MON1_BASE.address + Addresses.PARTY_OFFSET_HP
PARTY_MON_1_MAX_HP = Addresses.PARTY_MON1_BASE.address + Addresses.PARTY_OFFSET_MAX_HP
