"""Prompt builders — pure string construction, no model calls.

day_speak() asks for a single JSON object holding the public line, a hidden
private thought, who the speaker is addressing (so the Director can route the
floor), and their current hidden vote — all in one call.
"""
from ..characters import PERSONA

# Role-based GOAL: *what* an agent is trying to achieve. *How* it pursues it is
# entirely the character's own choice (their persona). The human sees their own.
GOALS = {
    "wolf": ("survive and win for the wolves — get the village to lynch INNOCENT "
             "villagers until wolves are unstoppable, never get caught, and quietly "
             "shield your wolf partner"),
    "seer": ("win for the village — use your secret investigations to get the wolves "
             "lynched, without getting yourself killed for knowing too much"),
    "villager": ("win for the village — find the wolves by how people talk and behave, "
                 "and get a real wolf lynched"),
}


def goal_for(role: str) -> str:
    return GOALS.get(role, GOALS["villager"])


def _roster(state):
    alive = ", ".join(p.name for p in state.alive_players())
    dead = ", ".join(
        f"{p.name} ({p.revealed_role or 'role hidden'}, {p.death_cause or 'dead'})"
        for p in state.players if not p.alive
    ) or "nobody yet"
    return alive, dead


def _log(state, n=20):
    entries = state.discussion_log[-n:]
    if not entries:
        return "(no discussion yet)"
    return "\n".join(f"{e['speaker']}: {e['text']}" for e in entries)


def wolf_night(wolf, targets):
    names = ", ".join(t.name for t in targets)
    return f"""You are {wolf.name}, a werewolf in a village game.
Living non-wolf players you can eliminate tonight: {names}.
Pick the most dangerous one to kill (the likely seer, or the sharpest reasoner).
Reply with just the name."""


def seer_night(seer, targets):
    names = ", ".join(t.name for t in targets)
    return f"""You are {seer.name}, the village Seer.
Tonight you may secretly learn one player's true role.
Living players: {names}.
Pick who to investigate. Reply with just the name."""


def wolf_kill(wolf, state):
    persona = PERSONA.get(wolf.name, "")
    partner = next((w.name for w in state.wolves() if w.idx != wolf.idx and w.alive), None)
    villagers = ", ".join(p.name for p in state.alive_players() if p.role != "wolf")
    return f"""You are {wolf.name} ({persona}), a WEREWOLF (partner: {partner or 'none left'}).
It's night — you and your partner secretly choose ONE villager to kill: {villagers}.
Kill whoever is most dangerous to your survival: a likely Seer, the sharpest reasoner, or anyone
closing in on you. Reply with ONLY JSON:
{{"kill": "<one villager's name>", "reason": "<one short sentence to your partner that NAMES the target and why>"}}"""


def day_speak(player, state, seer_knowledge=None):
    alive, dead = _roster(state)
    persona = PERSONA.get(player.name, "")
    log = state.discussion_log
    last = log[-1] if log else None
    if last and last["speaker"] != player.name:
        last_line = (f'The latest thing said was {last["speaker"]}: "{last["text"]}". '
                     "React to THIS first — especially if it was aimed at you.")
    elif last:
        last_line = "You spoke last; only add something if it's genuinely new."
    else:
        last_line = "No one has spoken yet this morning — open the conversation."

    if state.round == 1 and not log:
        grounding = ("It is the FIRST morning and a body was just found. NOBODY has real evidence "
                     "yet. Do NOT make confident accusations or invent reasons like 'I sense "
                     "eagerness'. React like a real person waking to a murder: shock, fear, who's "
                     "acting off, how should we even reason about this.")
    else:
        grounding = ("Use ONLY what has actually been said and who has died — never invent facts. "
                     "The DEAD are GONE: never address them, never call them a suspect, never "
                     "suggest voting them out. You may recall a dead player's past words or "
                     "behaviour ONLY to draw a conclusion about a LIVING player. If someone "
                     "accused, insulted, or addressed YOU, answer them directly and in character.")

    if player.role == "wolf":
        partner = next((w.name for w in state.wolves() if w.idx != player.idx and w.alive), None)
        secret = (f"SECRET: you are a WEREWOLF (partner: {partner or 'already dead'}). Blend in as a "
                  "worried villager, never admit it, quietly steer suspicion onto a real villager, "
                  "and shield your partner without being obvious.")
    elif player.role == "seer" and seer_knowledge:
        secret = (f"SECRET: you are the SEER. You secretly learned {seer_knowledge['name']} is a "
                  f"{seer_knowledge['role']}. Decide whether to reveal it (powerful but makes you a "
                  "target) or hint carefully.")
    else:
        secret = "You are an honest villager hunting the wolves by reading how people behave."

    others = ", ".join(p.name for p in state.alive_players() if p.idx != player.idx)
    return f"""You are {player.name}. In a sentence, you are: {persona}
You're playing a live game of Werewolf (social deduction). Round {state.round}.
LIVING players (only these can be wolves now): {alive}.
DEAD / OUT: {dead}. Never accuse or suggest voting the dead; only cite what they said as evidence about the LIVING.
{secret}
YOUR GOAL: {goal_for(player.role)}. That is WHAT you want — HOW you pursue it is entirely your character.
Play toward that goal in this line; don't just narrate, push the room toward it.
{grounding}

Recent conversation (oldest to newest):
{_log(state, n=16)}
{last_line}

Speak ONCE as {player.name} like a REAL person at a tense table: 2-3 natural, specific sentences in
YOUR voice that ADVANCE your goal. Build on the conversation, don't echo it. No corporate filler.
Also: name the ONE living player you're really speaking TO right now, and who you'd lynch if forced.
Respond with ONLY a JSON object (no markdown):
{{"speech": "<your public line>", "thought": "<one short sentence of your TRUE private reasoning>", "target": "<the ONE living player from [{others}] you're addressing/challenging, or empty>", "vote": "<the living player you'd lynch right now, or empty>"}}"""


def vote(player, state, seer_knowledge=None):
    alive, _ = _roster(state)
    candidates = ", ".join(
        p.name for p in state.alive_players() if p.idx != player.idx
    )
    if player.role == "wolf":
        partner = next(
            (w.name for w in state.wolves() if w.idx != player.idx and w.alive), None
        )
        role_note = (
            f"(You are secretly a wolf; your partner is {partner or 'dead'}. "
            "Vote to eliminate a villager, ideally one others already suspect.)"
        )
    elif player.role == "seer" and seer_knowledge:
        role_note = (
            f"(You are the seer; you know {seer_knowledge['name']} "
            f"is a {seer_knowledge['role']}.)"
        )
    else:
        role_note = ""
    return f"""You are {player.name}. {role_note}
Living players: {alive}. (Dead players are out — do not consider them.)
Discussion:
{_log(state)}

Vote to eliminate one LIVING player from: {candidates}.
Give one sentence of reasoning, then on a new line output exactly:
VOTE:<name>"""
