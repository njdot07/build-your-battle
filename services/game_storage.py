"""
services/game_storage.py
========================
Persistence layer for the Games Hub.

A "Game" is a bundle of rules + mode + arena preset.  Built-in games
ship with the app and can't be deleted; custom / AI-generated games
live in `custom_games.json` next to the main script.

Usage:
    library = GameLibrary.load()
    library.add(GameConfig(name="Glass Cannon", hp_mult=0.5, damage_mult=2.0))
    library.save()
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Optional


# The JSON file lives alongside the game so it's easy for users to
# back-up or delete (reset to defaults by deleting the file).
STORAGE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "custom_games.json",
)


# ---------------------------------------------------------------------------
# GameConfig — a single playable preset
# ---------------------------------------------------------------------------
VALID_MODES = ("classic", "quick_duel", "survival")
VALID_WIN_CONDITIONS = ("waves", "first_to_kos", "survival_time")
VALID_ABILITIES = ("double_jump", "reflect", "ground_slam",
                   "heal_pulse", "extra_shields")


@dataclass
class GameConfig:
    name:             str = "Unnamed Game"
    description:      str = ""
    mode:             str = "classic"           # classic | quick_duel | survival
    hp_mult:          float = 1.0
    damage_mult:      float = 1.0
    speed_mult:       float = 1.0
    gravity_mult:     float = 1.0
    time_limit:       int = 0                   # seconds; 0 = unlimited
    win_condition:    str = "waves"
    target_kos:       int = 3                   # used when win_condition=first_to_kos
    arena_tier:       int = -1                  # -1 = auto / wave-driven
    allowed_abilities: List[str] = field(default_factory=lambda: list(VALID_ABILITIES))
    source:           str = "custom"            # builtin | custom | ai
    id:               str = ""                  # unique id — assigned on save

    # ---- validation & normalisation ----
    def validate(self) -> "GameConfig":
        if self.mode not in VALID_MODES:
            self.mode = "classic"
        if self.win_condition not in VALID_WIN_CONDITIONS:
            self.win_condition = "waves"
        self.hp_mult = max(0.25, min(3.0, float(self.hp_mult)))
        self.damage_mult = max(0.25, min(3.0, float(self.damage_mult)))
        self.speed_mult = max(0.5, min(2.0, float(self.speed_mult)))
        self.gravity_mult = max(0.3, min(1.8, float(self.gravity_mult)))
        self.time_limit = max(0, min(600, int(self.time_limit)))
        self.target_kos = max(1, min(10, int(self.target_kos)))
        self.arena_tier = max(-1, min(5, int(self.arena_tier)))
        if not isinstance(self.allowed_abilities, list):
            self.allowed_abilities = list(VALID_ABILITIES)
        self.allowed_abilities = [a for a in self.allowed_abilities
                                  if a in VALID_ABILITIES]
        self.name = (self.name or "Unnamed Game")[:30]
        self.description = (self.description or "")[:120]
        return self

    def summary(self) -> str:
        """Short one-line rules summary for hub cards."""
        bits = []
        if self.hp_mult != 1.0: bits.append(f"HP x{self.hp_mult:g}")
        if self.damage_mult != 1.0: bits.append(f"DMG x{self.damage_mult:g}")
        if self.speed_mult != 1.0: bits.append(f"SPD x{self.speed_mult:g}")
        if self.gravity_mult != 1.0: bits.append(f"GRAV x{self.gravity_mult:g}")
        if self.time_limit > 0: bits.append(f"{self.time_limit}s limit")
        if self.win_condition == "first_to_kos":
            bits.append(f"First to {self.target_kos}")
        if len(self.allowed_abilities) < len(VALID_ABILITIES):
            bits.append(f"{len(self.allowed_abilities)} abilities")
        return "  ·  ".join(bits) if bits else "Standard rules"


# ---------------------------------------------------------------------------
# Default / built-in games
# ---------------------------------------------------------------------------
def _default_games() -> List[GameConfig]:
    return [
        GameConfig(
            id="builtin_classic",
            name="Classic Crucible",
            description="The original — climb the waves, beat the guardians.",
            mode="classic", win_condition="waves",
            source="builtin",
        ),
        GameConfig(
            id="builtin_duel",
            name="Quick Duel",
            description="One-arena brawl — first to 3 knockouts wins.",
            mode="quick_duel", win_condition="first_to_kos",
            target_kos=3, arena_tier=1,
            source="builtin",
        ),
        GameConfig(
            id="builtin_glass",
            name="Glass Cannon",
            description="Half HP, double damage. Every hit matters.",
            mode="quick_duel", win_condition="first_to_kos",
            target_kos=3, hp_mult=0.5, damage_mult=2.0, speed_mult=1.2,
            source="builtin",
        ),
        GameConfig(
            id="builtin_featherfall",
            name="Featherfall",
            description="Floaty low-gravity brawl with buffed speed.",
            mode="quick_duel", win_condition="first_to_kos",
            target_kos=2, gravity_mult=0.5, speed_mult=1.3,
            source="builtin",
        ),
    ]


# ---------------------------------------------------------------------------
# Library — the in-memory collection of games
# ---------------------------------------------------------------------------
class GameLibrary:
    def __init__(self, games: Optional[List[GameConfig]] = None):
        self.games: List[GameConfig] = games or []
        if not self.games:
            self.games = _default_games()

    # -- persistence ----------------------------------------------------
    @classmethod
    def load(cls, path: str = STORAGE_PATH) -> "GameLibrary":
        """Load games from disk, merging defaults + user customs.

        Built-ins are always present (rewritten from code each load so
        code-level changes propagate).  User entries persist via JSON.
        """
        defaults = _default_games()
        user_games: List[GameConfig] = []
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                for entry in raw.get("games", []):
                    if entry.get("source") == "builtin":
                        continue  # ignore persisted builtins
                    try:
                        user_games.append(GameConfig(**entry).validate())
                    except (TypeError, ValueError):
                        continue
            except (OSError, json.JSONDecodeError):
                pass
        return cls(games=defaults + user_games)

    def save(self, path: str = STORAGE_PATH) -> None:
        """Write only user/AI games (built-ins live in code)."""
        to_save = [asdict(g) for g in self.games
                   if g.source in ("custom", "ai")]
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"games": to_save}, f, indent=2)
        except OSError:
            pass  # silent — game continues even if disk is read-only

    # -- mutations ------------------------------------------------------
    def add(self, cfg: GameConfig) -> GameConfig:
        cfg.validate()
        if not cfg.id:
            cfg.id = self._new_id(cfg.name)
        # If id already exists, replace (edit scenario)
        for i, g in enumerate(self.games):
            if g.id == cfg.id:
                if g.source == "builtin":
                    return g  # can't overwrite builtin
                self.games[i] = cfg
                return cfg
        self.games.append(cfg)
        return cfg

    def delete(self, game_id: str) -> bool:
        for i, g in enumerate(self.games):
            if g.id == game_id:
                if g.source == "builtin":
                    return False
                self.games.pop(i)
                return True
        return False

    # -- helpers --------------------------------------------------------
    def _new_id(self, name: str) -> str:
        existing_ids = {g.id for g in self.games}
        base = "".join(c.lower() if c.isalnum() else "_" for c in name)[:20] or "game"
        candidate = base
        n = 2
        while candidate in existing_ids:
            candidate = f"{base}_{n}"
            n += 1
        return candidate
