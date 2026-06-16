"""Live-game persistence — snapshot the in-progress GameState to disk so a game
survives a backend restart (Render sleep / crash / redeploy).

Written after every phase (see phases.py). On boot the server restores the
snapshot and, if the game wasn't finished, resumes it from the next phase
(see loop.resume_game). Best-effort: persistence must never break the game.
"""
import json
from pathlib import Path

from .state import GameState, Player

_DATA = Path(__file__).resolve().parents[1] / "data"
_FILE = _DATA / "live.json"


def _to_dict(s: GameState) -> dict:
    return {
        "game_id": s.game_id,
        "theme": s.theme,
        "scene": s.scene,
        "phase": s.phase,
        "round": s.round,
        "max_rounds": s.max_rounds,
        "speaking_idx": s.speaking_idx,
        "players": [vars(p) for p in s.players],
        "night_result": s.night_result,
        "discussion_log": s.discussion_log,
        "private_reasoning": s.private_reasoning,
        "votes": s.votes,
        "winner": s.winner,
        "awaiting": s.awaiting,
        "seer_knowledge": s.seer_knowledge,
        "pending_kill_idx": s.pending_kill.idx if s.pending_kill else None,
    }


def _from_dict(d: dict) -> GameState:
    s = GameState(game_id=d["game_id"], max_rounds=d["max_rounds"])
    s.theme = d.get("theme", "fantasy")
    s.scene = d.get("scene", "scene1")
    s.phase = d["phase"]
    s.round = d["round"]
    s.awaiting = d.get("awaiting")
    s.speaking_idx = d["speaking_idx"]
    s.players = [Player(**p) for p in d["players"]]
    s.night_result = d["night_result"]
    s.discussion_log = d["discussion_log"]
    s.private_reasoning = d["private_reasoning"]
    s.votes = d["votes"]
    s.winner = d["winner"]
    s.seer_knowledge = d.get("seer_knowledge")
    pk = d.get("pending_kill_idx")
    s.pending_kill = s.players[pk] if pk is not None else None
    return s


def save(state: GameState) -> None:
    """Persist the current live game. Best-effort; never raises."""
    try:
        _DATA.mkdir(parents=True, exist_ok=True)
        _FILE.write_text(json.dumps(_to_dict(state)))
    except Exception as e:
        print(f"[livestate] save failed: {e}")


def load() -> GameState | None:
    """Restore the last live game, or None if there isn't one."""
    if not _FILE.exists():
        return None
    try:
        return _from_dict(json.loads(_FILE.read_text()))
    except Exception as e:
        print(f"[livestate] load failed: {e}")
        return None


def clear() -> None:
    try:
        _FILE.unlink(missing_ok=True)
    except Exception:
        pass
