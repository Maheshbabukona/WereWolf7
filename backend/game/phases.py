"""The six phases, each a function over (state, narrator).

Phases mutate GameState, drive pacing beats, delegate decisions to `agents`,
adjudication to `rules`, and narration to the narrator. They contain no
transport, parsing, or print logic of their own.
"""
import random
import time

from . import agents, human, livestate, rules
from .agents import director
from .config import config
from .narrator import Narrator
from .state import GameState, Player

HUMAN_FLOOR_TIMEOUT = 90   # seconds the human has the floor after raising a hand


def _beat(seconds: float) -> None:
    if config.pace > 0:
        time.sleep(seconds * config.pace)


def _readable_pause(text: str) -> None:
    """Hold a line on screen long enough to read (so one voice finishes before
    the Director cues the next) — but cut it short the instant the human raises a
    hand, so taking the floor stays responsive. Skipped at PACE=0 (tests)."""
    if config.pace <= 0:
        return
    end = time.time() + min(13.0, max(3.0, len(text or "") / 24))
    while time.time() < end:
        if human.peek_hand():
            return
        time.sleep(0.15)


def _add_speech(state: GameState, speaker: str, text: str) -> None:
    state.discussion_log.append(
        {"round": state.round, "speaker": speaker, "text": text, "ts": int(time.time())}
    )


def _set_vote(state: GameState, voter: str, target: str) -> None:
    """Set/replace a voter's hidden vote (validated to a living other player)."""
    t = state.by_name(target)
    state.votes = [v for v in state.votes if v["voter"] != voter]
    if t and t.alive and t.name != voter:
        state.votes.append({"voter": voter, "target": t.name})


def setup(state: GameState, nar: Narrator) -> None:
    state.phase = "setup"
    nar.emit("setup", roster=[(p.name, p.role) for p in state.players])
    _beat(2)
    livestate.save(state)


def _wait_night_action(state: GameState, deadline: float, options: list[str]) -> str | None:
    """Poll the human's night choice until they pick a valid option or time ends."""
    human.set_night_action(None)
    while time.time() < deadline and not state.aborted:
        a = human.get_night_action()
        if a and a in options:
            return a
        time.sleep(0.2)
    return None


def _seer_investigate(state: GameState, deadline: float):
    """(seer, investigated_target) — the human seer picks; an agent seer auto-picks."""
    seer = next((p for p in state.alive_players() if p.role == "seer"), None)
    if not seer:
        return None, None
    targets = [p for p in state.alive_players() if p.idx != seer.idx]
    if seer.is_human:
        state.awaiting = {"kind": "seer", "options": [t.name for t in targets]}
        livestate.save(state)
        picked = _wait_night_action(state, deadline, [t.name for t in targets])
        state.awaiting = None
        target = state.by_name(picked) or random.choice(targets)
    else:
        _, target = agents.night_seer_pick(state)
    return seer, target


def _wolf_kill(state: GameState, deadline: float) -> Player | None:
    """Wolves agree on a kill (time-based). Agent wolves each reason + pick a
    NAMED target (shown to the pack in the wolves-only channel + a live vote
    tally); the human wolf picks via the night panel and can change until the
    night ends. The most-voted villager dies (a kill always happens)."""
    wolves = state.alive_wolves()
    villagers = [p for p in state.alive_players() if p.role != "wolf"]
    if not villagers:
        return None
    state.wolf_chat = []
    state.wolf_votes = {}
    for w in wolves:
        if w.is_human:
            continue
        victim, line = agents.wolf_kill_suggest(w, state)
        victim = victim or random.choice(villagers)
        state.wolf_votes[w.name] = victim.name
        state.wolf_chat.append({"speaker": w.name, "target": victim.name, "text": line or ""})
    livestate.save(state)

    hw = next((w for w in wolves if w.is_human), None)
    if hw:
        opts = [v.name for v in villagers]
        state.awaiting = {"kind": "wolf_kill", "options": opts}
        livestate.save(state)
        # Let the human watch the pack's votes and change theirs until the timer.
        while time.time() < deadline and not state.aborted:
            a = human.get_night_action()
            if a and a in opts:
                state.wolf_votes[hw.name] = a
            time.sleep(0.2)
        state.awaiting = None
        if hw.name not in state.wolf_votes:
            state.wolf_votes[hw.name] = random.choice(opts)

    counts: dict[str, int] = {}
    for name in state.wolf_votes.values():
        counts[name] = counts.get(name, 0) + 1
    top = max(counts.values())
    finalists = [n for n, c in counts.items() if c == top]   # break ties so a kill always happens
    return state.by_name(random.choice(finalists)) or random.choice(villagers)


def night(state: GameState, nar: Narrator) -> None:
    state.phase = "night"
    state.speaking_idx = None
    human.reset()
    deadline = time.time() + config.night_seconds
    nar.emit("night_start")
    livestate.save(state)

    seer, target = _seer_investigate(state, deadline)
    state.seer_knowledge = (
        {"name": target.name, "role": target.role} if target else None
    )
    victim = _wolf_kill(state, deadline)
    state.pending_kill = victim
    state.awaiting = None
    nar.emit(
        "night",
        victim=victim.name if victim else None,
        seer=seer.name if seer else None,
        target=target.name if target else None,
        target_role=target.role if target else None,
    )
    livestate.save(state)


def morning(state: GameState, nar: Narrator) -> None:
    state.phase = "morning"
    v = state.pending_kill
    if v:
        rules.eliminate(v)
        v.death_cause = "killed in the night"
        state.night_result = {"victimName": v.name, "victimIdx": v.idx}
        nar.emit("morning", victim=v.name, role=v.role)
    _beat(2)
    livestate.save(state)


def _human_floor(state: GameState, nar: Narrator, h: Player, deadline: float) -> str | None:
    """The human raised a hand: hold the agents and give them the floor. Blank the
    stage first so no STALE line from last time shows while they compose. Bounded
    by the (continuous) day timer, never beyond it."""
    h.current_speech = None
    state.speaking_idx = None
    state.awaiting = {"kind": "speak", "playerIdx": h.idx}
    livestate.save(state)
    human.begin()
    text = human.wait(min(HUMAN_FLOOR_TIMEOUT, max(2.0, deadline - time.time())))
    state.awaiting = None
    if text and text.strip():
        text = text.strip()
        _add_speech(state, h.name, text)
        state.speaking_idx = h.idx
        h.current_speech = text
        nar.emit("speech", name=h.name, text=text)
        livestate.save(state)
        return text
    return None


def day(state: GameState, nar: Narrator) -> None:
    """The director-orchestrated, time-based daytime debate.

    One agent holds the floor at a time (readable), chosen by the Director from
    who was addressed + provocation + goals. The human RAISES A HAND to take the
    floor; agents hold for them and then answer them. Voting is a hidden ballot
    that each agent updates as they speak; when the timer runs out we tally it
    and eliminate the most-suspected player (the only thing revealed)."""
    state.phase = "day"
    state.votes = []
    state.day_result = None     # clear last round's lynch banner
    human.reset()
    h = state.human_player()
    deadline = time.time() + config.day_seconds
    state.day_ends_at = deadline
    nar.emit("day_start")
    livestate.save(state)

    last_idx: int | None = None
    last_spoke: dict[int, float] = {}
    directed_target: str | None = None
    reply_to_human: str | None = None

    while time.time() < deadline and not state.aborted:
        now = time.time()

        # 1) Human asked for the floor -> hand it over (agents wait). The day
        #    timer keeps running continuously (one clock for the whole debate).
        if h and h.alive and human.take_hand():
            line = _human_floor(state, nar, h, deadline)
            if line:
                reply_to_human = line
                last_idx, last_spoke[h.idx], directed_target = h.idx, time.time(), None
                _readable_pause(line)   # keep YOUR line on stage before an agent replies
            continue

        # 2) Read the human's hidden vote (any time).
        if h and h.alive:
            hv = human.get_vote()
            if hv is not None:
                _set_vote(state, h.name, hv)

        # 3) Director cues the next voice.
        if reply_to_human:
            sp = director.respond_to_human(state, reply_to_human, last_spoke, now)
            reply_to_human = None
        else:
            sp = director.next_speaker(state, last_idx, directed_target, last_spoke, now)
        if sp is None:
            break  # nobody left to speak

        sk = state.seer_knowledge if sp.role == "seer" else None
        speech, thought, target, vote = agents.speak(sp, state, sk)
        state.speaking_idx = sp.idx
        sp.current_speech = speech
        _add_speech(state, sp.name, speech)
        state.private_reasoning.append({"speaker": sp.name, "role": sp.role, "thought": thought})
        if vote:
            _set_vote(state, sp.name, vote)
        nar.emit("speech", name=sp.name, text=speech)
        directed_target = target or None
        last_idx, last_spoke[sp.idx] = sp.idx, time.time()
        livestate.save(state)
        _readable_pause(speech)   # readable pacing; ends early if you raise a hand

    # Human left the game -> bail without lynching anyone.
    if state.aborted:
        state.awaiting = state.day_ends_at = state.speaking_idx = None
        state.phase = "resolution"
        return

    # Resolve: lock the human's final secret vote, then tally the hidden ballot.
    state.awaiting = None
    state.day_ends_at = None
    state.speaking_idx = None
    for p in state.players:
        p.current_speech = None
    if h and h.alive:
        _set_vote(state, h.name, human.get_vote() or "")
    out = rules.tally(state)
    if out:
        rules.eliminate(out)
        out.death_cause = "voted out by the village"
        state.day_result = {"name": out.name, "role": out.role}
        nar.emit("eliminated", name=out.name, role=out.role)
    else:
        state.day_result = {"name": None}
        nar.emit("no_elimination")
    state.phase = "resolution"
    _beat(1)
    livestate.save(state)


def end(state: GameState, nar: Narrator) -> None:
    state.phase = "ended"
    if not state.winner:
        state.winner = rules.final_winner(state)
    for p in state.players:
        p.revealed_role = p.role
    nar.emit(
        "game_over",
        winner=state.winner,
        roles=[(p.name, p.role) for p in state.players],
    )
    livestate.save(state)
