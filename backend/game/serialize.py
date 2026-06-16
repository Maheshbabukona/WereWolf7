"""GameState -> client JSON, with server-side fog of war.

The ONLY place game state crosses to a client. Fog rules are mandatory and
enforced here, never on the client:
  - mode=god:    return everything (spectator).
  - mode=player: hide role unless revealed; reveal the HUMAN player's OWN role
                 + secret knowledge (so they can play); surface `awaiting`/`you`.
"""
import time

from . import human, rules
from .agents.prompts import goal_for
from .config import config
from .state import GameState


def _player(p, mode: str, human_idx: int | None) -> dict:
    show = (
        mode == "god"
        or p.revealed_role is not None
        or (mode == "player" and p.idx == human_idx)
    )
    return {
        "idx": p.idx,
        "name": p.name,
        "avatar": p.avatar,
        "avatarSeed": p.name,   # fallback seed for procedural avatars
        "alive": p.alive,
        "role": p.role if show else None,
        "revealedRole": p.revealed_role,
        "currentSpeech": p.current_speech,
        "isHuman": p.is_human,
    }


def _you(state: GameState) -> dict | None:
    """The human player's private view of themselves (role + secret)."""
    h = state.human_player()
    if not h:
        return None
    # The displayed vote is the human's OWN live intent (instant), not the loop's
    # last-synced tally — so the button reflects clicks immediately.
    you = {"idx": h.idx, "name": h.name, "avatar": h.avatar, "role": h.role,
           "alive": h.alive, "goal": goal_for(h.role), "vote": human.get_vote() or None}
    if h.role == "seer" and state.seer_knowledge:
        you["seer"] = state.seer_knowledge
    if h.role == "wolf":
        you["partner"] = next((w.name for w in state.wolves() if w.idx != h.idx), None)
        you["wolfChat"] = state.wolf_chat            # wolves-only night channel
        you["wolfVotes"] = state.wolf_votes          # who each wolf is voting to kill
    return you


def to_client(state: GameState, mode: str = "player") -> dict:
    human_idx = state.human_player().idx if state.human_player() else None
    out = {
        "gameId": state.game_id,
        "theme": state.theme,
        "scene": state.scene,
        "phase": state.phase,
        "round": state.round,
        "maxRounds": state.max_rounds,
        "speakingIdx": state.speaking_idx,
        "players": [_player(p, mode, human_idx) for p in state.players],
        "nightResult": state.night_result,
        "dayResult": state.day_result,     # who was lynched (name + role), no ballot
        "discussionLog": state.discussion_log,
        # Live vote VISIBILITY: counts per living player + who has cast a vote
        # (the per-voter TARGET stays secret — no who-voted-for-whom).
        "voteCounts": rules.vote_counts(state) if state.phase == "day" else {},
        "voters": sorted({v["voter"] for v in state.votes}) if state.phase == "day" else [],
        "aliveCount": len(state.alive_players()),
        "daySecondsLeft": (
            max(0, int(state.day_ends_at - time.time())) if state.day_ends_at else None
        ),
        "winner": state.winner,
        "agentProvider": "mock" if config.use_mock else config.openai_model,
    }
    if mode == "god":
        out["privateReasoning"] = state.private_reasoning
    if mode == "player":
        out["you"] = _you(state)
        out["awaiting"] = state.awaiting
    return out
