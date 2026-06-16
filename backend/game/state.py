"""Core data model for a Werewolf game.

Pure data — no LLM, no I/O. The loop mutates a single GameState instance in
place; the FastAPI layer serializes it (with fog of war).
"""
from dataclasses import dataclass, field


@dataclass
class Player:
    idx: int
    name: str
    role: str                       # "wolf" | "seer" | "villager"
    avatar: str | None = None       # cosmetic sprite slug (see avatars.py)
    alive: bool = True
    revealed_role: str | None = None
    death_cause: str | None = None  # "killed in the night" | "voted out by the village"
    current_speech: str | None = None
    is_human: bool = False          # a human-controlled seat


@dataclass
class GameState:
    game_id: int = 1
    theme: str = "fantasy"          # art family (see themes.py)
    scene: str = "scene1"           # chosen backdrop within the theme
    phase: str = "setup"            # setup|night|morning|day|resolution|ended
    round: int = 1
    max_rounds: int = 8             # safety cap; the game really ends on a faction win
    speaking_idx: int | None = None
    day_ends_at: float | None = None  # epoch when the day's debate timer expires
    players: list[Player] = field(default_factory=list)
    night_result: dict | None = None
    day_result: dict | None = None     # who the village lynched (name + role), no ballot
    discussion_log: list[dict] = field(default_factory=list)
    wolf_chat: list[dict] = field(default_factory=list)   # wolves-only night channel
    wolf_votes: dict = field(default_factory=dict)        # wolf_name -> kill target (wolves only)
    private_reasoning: list[dict] = field(default_factory=list)
    votes: list[dict] = field(default_factory=list)
    winner: str | None = None
    aborted: bool = False              # human left the game -> bail out
    # When set, the loop is blocked waiting for a human player's input.
    # e.g. {"kind": "speak", "playerIdx": 3} or {"kind": "vote", "playerIdx": 3, "options": [...]}
    awaiting: dict | None = None

    # transient per-round scratch (never serialized to clients)
    seer_knowledge: dict | None = None
    pending_kill: "Player | None" = None

    def human_player(self) -> "Player | None":
        return next((p for p in self.players if p.is_human), None)

    def alive_players(self) -> list[Player]:
        return [p for p in self.players if p.alive]

    def wolves(self) -> list[Player]:
        return [p for p in self.players if p.role == "wolf"]

    def alive_wolves(self) -> list[Player]:
        return [p for p in self.players if p.role == "wolf" and p.alive]

    def by_name(self, name: str) -> Player | None:
        if not name:
            return None
        return next((p for p in self.players if p.name.lower() == name.lower()), None)
