"""The Director — orchestrates WHO holds the floor next, with no LLM call.

Like a showrunner pulling strings. It's NOT round-robin: after each line it
routes the floor by who was just *addressed*, who got provoked, persona, goal
relevance, and a cooldown so nobody monologues. One agent speaks at a time
(serialized + readable); autonomy is in the *choice* of speaker, not in everyone
talking at once.

  • next_speaker(...) picks the agent to take the floor (or None for a beat).
  • respond_to_human(...) picks who answers the human after they raise a hand.
"""
import random
import re

from ..characters import PERSONA

_LOUD = ("dominant", "confrontational", "provok", "sarcas", "liar", "charismatic",
         "short-tempered", "manipulat", "skeptic", "chaos", "pressure")
_QUIET = ("patient", "calculating", "speaks little", "quiet", "empath",
          "observant", "reveals so little", "diplomatic", "keep peace")


def chattiness(name: str) -> float:
    p = (PERSONA.get(name, "") or "").lower()
    score = 0.5 + 0.12 * sum(k in p for k in _LOUD) - 0.12 * sum(k in p for k in _QUIET)
    return max(0.1, min(0.95, score))


def _named_in(name: str, text: str) -> bool:
    return bool(re.search(rf"\b{re.escape(name.split()[0])}\b", text or "", re.IGNORECASE))


def _agents(state):
    return [p for p in state.alive_players() if not p.is_human]


def _score(state, p, last_idx, last_text, last_spoke, now):
    since = now - last_spoke.get(p.idx, 0.0)
    s = chattiness(p.name) + random.uniform(0.0, 0.35)
    if _named_in(p.name, last_text):
        s += 1.4                       # was just referenced -> wants to respond
    s += min(0.6, since / 22.0)        # quiet for a while -> nudge
    if p.idx == last_idx:
        s -= 1.5                        # don't speak twice in a row
    elif since < 4.0:
        s -= 0.6
    return s


def next_speaker(state, last_idx, directed_target, last_spoke, now):
    """Whoever the Director hands the floor to next.

    Priority: a player the last speaker explicitly addressed -> heuristic pick.
    Returns a living agent (the debate flows continuously until the timer)."""
    agents = _agents(state)
    if not agents:
        return None
    last = state.discussion_log[-1] if state.discussion_log else None
    last_text = last["text"] if last else ""

    # 1) Honour the last speaker's declared target (the "pulling strings" part).
    if directed_target:
        t = state.by_name(directed_target)
        if t and t.alive and not t.is_human and t.idx != last_idx and (now - last_spoke.get(t.idx, 0)) > 3.0:
            return t

    # 2) Otherwise score the room and pick the most-compelled voice.
    return max(agents, key=lambda p: _score(state, p, last_idx, last_text, last_spoke, now))


def respond_to_human(state, human_text, last_spoke, now):
    """Who answers the human after they take the floor (never None if any agent)."""
    agents = _agents(state)
    if not agents:
        return None
    # An agent the human named answers; else the most reactive voice.
    named = next((p for p in agents if _named_in(p.name, human_text)), None)
    if named:
        return named
    return max(agents, key=lambda p: chattiness(p.name) + random.uniform(0, 0.5)
              + min(0.5, (now - last_spoke.get(p.idx, 0)) / 20.0))
