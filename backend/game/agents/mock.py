"""Keyless mock behaviour — plausible decisions with no API key, no cost.

Used when config.use_mock is True so the full game (and the whole UI) is
verifiable and demo-safe before any OpenAI key is provided.
"""
import random

_LINES = [
    "Something about last night doesn't sit right with me.",
    "I've been watching the voting patterns and one of you stands out.",
    "Let's not rush, but I do have a suspicion forming.",
    "Whoever's quiet right now is exactly who I'd watch.",
    "I'll say it plainly: that explanation was too convenient.",
    "We can't afford another wasted vote. Think it through.",
    "I trusted that read earlier and now I'm second-guessing it.",
    "The math points one direction and I don't like where it lands.",
]


def wolf_pick(state):
    targets = [p for p in state.alive_players() if p.role != "wolf"]
    seer = next((t for t in targets if t.role == "seer"), None)
    return seer if (seer and random.random() < 0.6) else random.choice(targets)


def seer_pick(seer, targets):
    return random.choice(targets)


def speak(player, state, seer_knowledge):
    """(speech, thought, target, vote) — reactive-ish canned behaviour."""
    others = [p.name for p in state.alive_players() if p.idx != player.idx]
    last = state.discussion_log[-1] if state.discussion_log else None
    if last and last["speaker"] != player.name:
        target = last["speaker"]
        line = random.choice([
            f"{target}, that's a convenient thing to say right now.",
            f"I'm not buying what {target} just told us.",
            f"Fair point, {target}, but it doesn't clear you.",
        ])
    else:
        target = random.choice(others) if others else ""
        line = random.choice(_LINES)
    if player.role == "wolf":
        thought = f"(wolf) Steer the heat toward {target or 'someone'}, keep my partner clean."
    elif player.role == "seer" and seer_knowledge:
        thought = f"(seer) I know {seer_knowledge['name']} is a {seer_knowledge['role']}; holding it."
    else:
        thought = f"(villager) Genuinely unsure, leaning toward {target or 'someone'}."
    vote = target if (target in others and random.random() < 0.5) else ""
    return line, thought, target, vote


def vote(player, state, candidates: list[str]) -> str:
    if player.role == "wolf":
        prey = [
            p.name
            for p in state.alive_players()
            if p.role != "wolf" and p.idx != player.idx
        ]
        if prey:
            return random.choice(prey)
    if player.role == "seer" and state.seer_knowledge:
        known = state.seer_knowledge
        if known["role"] == "wolf" and known["name"] in candidates:
            return known["name"]
    return random.choice(candidates)
