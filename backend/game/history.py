"""Game history persistence — JSON file on disk (DB later for production).

Records each completed game (winner, roles, full discussion, votes) so the
frontend can show past matches and the data survives restarts.
"""
import json
import time
from pathlib import Path

from .state import GameState

_DATA = Path(__file__).resolve().parents[1] / "data"
_FILE = _DATA / "history.json"


def load() -> list[dict]:
    if _FILE.exists():
        try:
            return json.loads(_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return []
    return []


def next_game_id() -> int:
    games = load()
    return max((g.get("gameId", 0) for g in games), default=0) + 1


def record(state: GameState) -> None:
    """Append a completed game's summary. Best-effort; never raises."""
    try:
        _DATA.mkdir(parents=True, exist_ok=True)
        games = load()
        games.append(
            {
                "gameId": state.game_id,
                "winner": state.winner,
                "rounds": state.round,
                "endedAt": int(time.time()),
                "players": [
                    {"name": p.name, "role": p.role} for p in state.players
                ],
                "discussionLog": state.discussion_log,
                "votes": state.votes,
            }
        )
        _FILE.write_text(json.dumps(games, indent=2))
    except Exception as e:  # persistence must never break the game
        print(f"[history] failed to record game: {e}")
