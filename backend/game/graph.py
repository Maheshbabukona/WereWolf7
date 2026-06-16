"""LangGraph orchestration — the game flow as a StateGraph.

Topology (phases are nodes; conditional edges drive the round-loop + win-check):

    START → setup → night → morning ─┬─(decided)→ end → END
                                     └─→ discussion → voting ─┬─(decided | last round)→ end
                                                              └─→ next_round → night ↺

The graph's own state (`Flow`) is intentionally tiny — just routing info. The
heavy GameState is a single shared object the nodes mutate in place, so the
FastAPI /state poll keeps seeing live progress (each speech) at 2 Hz.
"""
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from . import phases, rules
from .narrator import Narrator
from .state import GameState


class Flow(TypedDict):
    round: int
    decided: bool


def _winner_set(state: GameState) -> bool:
    w = rules.decided_winner(state)
    if w:
        state.winner = w
    return w is not None


def build_graph(state: GameState, nar: Narrator):
    """Compile a graph whose nodes operate on the shared `state`/`nar`."""

    def setup_node(_flow: Flow):
        phases.setup(state, nar)
        return {}

    def night_node(flow: Flow):
        state.round = flow["round"]
        nar.emit("round", n=flow["round"])
        phases.night(state, nar)
        return {}

    def morning_node(_flow: Flow):
        phases.morning(state, nar)
        return {"decided": _winner_set(state)}

    def day_node(_flow: Flow):
        phases.day(state, nar)
        return {"decided": _winner_set(state)}

    def next_round_node(flow: Flow):
        return {"round": flow["round"] + 1}

    def end_node(_flow: Flow):
        phases.end(state, nar)
        return {}

    def after_morning(flow: Flow) -> str:
        return "end" if (flow["decided"] or state.aborted) else "day"

    def after_day(flow: Flow) -> str:
        if flow["decided"] or state.aborted or flow["round"] >= state.max_rounds:
            return "end"
        return "next_round"

    g = StateGraph(Flow)
    g.add_node("setup", setup_node)
    g.add_node("night", night_node)
    g.add_node("morning", morning_node)
    g.add_node("day", day_node)
    g.add_node("next_round", next_round_node)
    g.add_node("end", end_node)

    g.add_edge(START, "setup")
    g.add_edge("setup", "night")
    g.add_edge("night", "morning")
    g.add_conditional_edges("morning", after_morning, {"end": "end", "day": "day"})
    g.add_conditional_edges("day", after_day, {"end": "end", "next_round": "next_round"})
    g.add_edge("next_round", "night")
    g.add_edge("end", END)
    return g.compile()
