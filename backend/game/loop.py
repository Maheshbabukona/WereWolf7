"""Game runner — drives the LangGraph orchestration.

Thin: it holds the shared GameState global (read by the FastAPI layer while a
game runs in a background thread), builds the graph, and invokes it. All flow
topology lives in `graph.py`, all phase work in `phases.py`, adjudication in
`rules`, narration in the injected `Narrator`.
"""
from . import graph as game_graph
from . import history, phases, rules
from .narrator import ConsoleNarrator, Narrator, SilentNarrator
from .state import GameState

STATE: GameState | None = None

# Headroom for a game that may run several night/day rounds until a faction wins.
_RECURSION_LIMIT = 200

# The phases that make up one round, in order (used by the resume driver).
_ROUND_PHASES = ["night", "morning", "day"]


def run_game(state: GameState, nar: Narrator | None = None) -> GameState:
    """Fresh game — orchestrated by the LangGraph flow in graph.py."""
    global STATE
    STATE = state
    nar = nar or SilentNarrator()
    compiled = game_graph.build_graph(state, nar)
    compiled.invoke(
        {"round": 1, "decided": False},
        config={"recursion_limit": _RECURSION_LIMIT},
    )
    history.record(state)
    return state


def resume_game(state: GameState, nar: Narrator | None = None) -> GameState:
    """Continue a game restored from a disk snapshot after a backend restart.

    Snapshots are written AFTER each phase, so `state.phase` is the last fully
    completed phase; we re-enter at the NEXT phase. Phase logic is shared with
    the fresh path (both call the same phases.* functions), so behaviour is
    identical — only the sequencing is mirrored here (LangGraph drives fresh
    games; this small driver drives resumes)."""
    global STATE
    STATE = state
    nar = nar or SilentNarrator()

    # If the game was already decided when it died (before end() ran), finish it.
    if state.phase != "ended":
        decided = rules.decided_winner(state)
        if decided:
            state.winner = decided
            phases.end(state, nar)
            history.record(state)
            return state

    resume_map = {
        "setup": (1, "night"),
        "night": (state.round, "morning"),
        "morning": (state.round, "day"),
        "day": (state.round + 1, "night"),
        "resolution": (state.round + 1, "night"),
    }
    if state.phase not in resume_map:
        return state  # ended/unknown — nothing to resume
    from_round, from_phase = resume_map[state.phase]
    _play(state, nar, from_round, from_phase)
    history.record(state)
    return state


def _play(state: GameState, nar: Narrator, from_round: int, from_phase: str) -> None:
    """Run remaining phases from (from_round, from_phase) to game end."""
    for rnd in range(from_round, state.max_rounds + 1):
        state.round = rnd
        start = (
            _ROUND_PHASES.index(from_phase)
            if (rnd == from_round and from_phase in _ROUND_PHASES)
            else 0
        )
        if start == 0:
            nar.emit("round", n=rnd)
        for ph in _ROUND_PHASES[start:]:
            getattr(phases, ph)(state, nar)
            if ph in ("morning", "day"):
                decided = rules.decided_winner(state)
                if decided:
                    state.winner = decided
                    phases.end(state, nar)
                    return
        from_phase = "night"
    phases.end(state, nar)


if __name__ == "__main__":
    from .roster import new_game

    run_game(new_game(), ConsoleNarrator())
