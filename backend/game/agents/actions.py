"""Public agent API: the four decisions an agent makes during a game.

This is the only agent module the engine imports. It chooses between the mock
and the real LLM path (via config), delegating transport to `llm` and output
parsing to `parse`. Returns are always concrete game objects, never raw text.

Resilience: every real LLM path is wrapped so a timeout/error falls back to the
mock behaviour. A stalled model call can therefore never freeze the narration —
the game keeps progressing with a stand-in line/pick.
"""
import random

from ..config import config
from . import llm, mock, parse, prompts


def night_wolf_pick(state):
    """Which non-wolf the wolves kill tonight."""
    targets = [p for p in state.alive_players() if p.role != "wolf"]
    if config.use_mock:
        return mock.wolf_pick(state)
    try:
        wolf = state.alive_wolves()[0]
        text = llm.chat(prompts.wolf_night(wolf, targets), max_tokens=60)
        picked = parse.name(text, [t.name for t in targets])
        return state.by_name(picked) or random.choice(targets)
    except Exception as e:
        print(f"[agents] night_wolf_pick LLM failed ({e}); mock fallback")
        return mock.wolf_pick(state)


def wolf_kill_suggest(player, state):
    """A single wolf's kill choice + one line to its partner -> (victim, reason)."""
    villagers = [p for p in state.alive_players() if p.role != "wolf"]
    if not villagers:
        return None, None
    if config.use_mock:
        v = mock.wolf_pick(state)
        return v, f"{v.name} feels like the safest one to take out tonight."
    try:
        raw = llm.chat(prompts.wolf_kill(player, state), json_mode=True, max_tokens=90)
        picked, reason = parse.kill(raw, [v.name for v in villagers])
        return (state.by_name(picked) if picked else mock.wolf_pick(state)), (reason or None)
    except Exception as e:
        print(f"[agents] wolf_kill_suggest LLM failed ({e}); mock fallback")
        return mock.wolf_pick(state), None


def night_seer_pick(state):
    """(seer, investigated_target) or (None, None) if no living seer."""
    seer = next((p for p in state.alive_players() if p.role == "seer"), None)
    if not seer:
        return None, None
    targets = [p for p in state.alive_players() if p.idx != seer.idx]
    if config.use_mock:
        return seer, mock.seer_pick(seer, targets)
    try:
        text = llm.chat(prompts.seer_night(seer, targets), max_tokens=60)
        picked = parse.name(text, [t.name for t in targets])
        return seer, (state.by_name(picked) or random.choice(targets))
    except Exception as e:
        print(f"[agents] night_seer_pick LLM failed ({e}); mock fallback")
        return seer, mock.seer_pick(seer, targets)


def speak(player, state, seer_knowledge=None):
    """One LLM call -> (public speech, private thought, target_name, vote_name).

    `target_name` is who they're addressing (the Director routes the floor there);
    `vote_name` is their current hidden lynch choice. Both validated to living
    players (or "")."""
    if config.use_mock:
        return mock.speak(player, state, seer_knowledge)
    try:
        raw = llm.chat(prompts.day_speak(player, state, seer_knowledge), json_mode=True, max_tokens=240)
        speech, thought, target, vote = parse.speak(raw)
        living = {p.name.lower(): p.name for p in state.alive_players() if p.idx != player.idx}
        target = living.get(target.lower(), "")
        vote = living.get(vote.lower(), "")
        return speech, thought, target, vote
    except Exception as e:
        print(f"[agents] speak LLM failed ({e}); mock fallback")
        return mock.speak(player, state, seer_knowledge)


def vote(player, state, seer_knowledge=None):
    """(target_player, raw_reasoning_text)."""
    candidates = [p.name for p in state.alive_players() if p.idx != player.idx]
    if config.use_mock:
        return state.by_name(mock.vote(player, state, candidates)), "(mock vote)"
    try:
        text = llm.chat(prompts.vote(player, state, seer_knowledge), max_tokens=120)
        picked = parse.vote(text, candidates)
        target = state.by_name(picked)
        if not target or target.idx == player.idx:
            target = state.by_name(random.choice(candidates))
        return target, text
    except Exception as e:
        print(f"[agents] vote LLM failed ({e}); mock fallback")
        return state.by_name(mock.vote(player, state, candidates)), "(mock vote)"
