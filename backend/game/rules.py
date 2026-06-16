"""Pure game rules. No I/O, no LLM, no chain — just functions over GameState.

Kept separate so the win/elimination logic is trivially testable and the phase
orchestration stays about *sequencing*, not *adjudication*.
"""
from .state import GameState, Player


def decided_winner(state: GameState) -> str | None:
    """Return 'village' / 'wolves' if the game is over, else None."""
    alive_wolves = state.alive_wolves()
    alive_village = [p for p in state.alive_players() if p.role != "wolf"]
    if len(alive_wolves) == 0:
        return "village"
    if len(alive_wolves) >= len(alive_village):
        return "wolves"
    return None


def final_winner(state: GameState) -> str:
    """Winner to declare at game end (falls back to wolves if undecided)."""
    return decided_winner(state) or ("village" if not state.alive_wolves() else "wolves")


def current_votes(state: GameState) -> dict[str, str]:
    """Latest hidden vote per voter (voter_name -> target_name); later overrides."""
    out: dict[str, str] = {}
    for v in state.votes:
        out[v["voter"]] = v["target"]
    return out


def vote_counts(state: GameState) -> dict[str, int]:
    """Live tally — how many votes each LIVING player currently has (name -> n)."""
    counts: dict[str, int] = {}
    for target in current_votes(state).values():
        t = state.by_name(target)
        if t and t.alive:
            counts[t.name] = counts.get(t.name, 0) + 1
    return counts


def tally(state: GameState) -> Player | None:
    """Most-voted LIVING player from the ballot, or None if nobody voted."""
    counts = vote_counts(state)
    if not counts:
        return None
    return state.by_name(max(counts, key=counts.get))


def eliminate(player: Player) -> None:
    """Kill a player and publicly reveal their role."""
    player.alive = False
    player.revealed_role = player.role
