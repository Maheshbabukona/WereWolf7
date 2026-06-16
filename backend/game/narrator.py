"""Presentation seam. Phases emit structured events; a Narrator renders them.

This keeps print() out of the game logic entirely. The console runner uses
ConsoleNarrator; the FastAPI server uses SilentNarrator (the UI is the view).
"""


class Narrator:
    """No-op base. Phases call narrator.emit(kind, **data)."""

    def emit(self, kind: str, **data) -> None:
        pass


class SilentNarrator(Narrator):
    pass


class ConsoleNarrator(Narrator):
    def emit(self, kind: str, **data) -> None:
        handler = getattr(self, f"_on_{kind}", None)
        if handler:
            handler(**data)

    # --- event handlers -------------------------------------------------- #
    def _on_setup(self, roster):
        print("\n--- SETUP ---", flush=True)
        print("Roster:", ", ".join(f"{n}({r})" for n, r in roster), flush=True)

    def _on_round(self, n):
        print(f"\n========== ROUND {n} ==========", flush=True)

    def _on_night(self, victim, seer, target, target_role):
        print("\n--- NIGHT --- (the village sleeps)", flush=True)
        print(f"  Wolves chose to kill: {victim}", flush=True)
        if seer and target:
            print(f"  Seer {seer} investigated {target} -> {target_role}", flush=True)

    def _on_morning(self, victim, role):
        print(f"\n--- MORNING --- {victim} was found dead. They were a {role}.", flush=True)

    def _on_discussion_start(self):
        print("\n--- DISCUSSION ---", flush=True)

    def _on_subround(self, n):
        print(f"  [sub-round {n}]", flush=True)

    def _on_speech(self, name, text):
        print(f"    {name}: {text}", flush=True)

    def _on_voting_start(self):
        print("\n--- VOTING ---", flush=True)

    def _on_vote(self, voter, target):
        print(f"  {voter} votes {target}", flush=True)

    def _on_eliminated(self, name, role):
        print(f"  -> {name} is voted out. They were a {role}.", flush=True)

    def _on_game_over(self, winner, roles):
        print(f"\n========== GAME OVER: {winner.upper()} WIN ==========", flush=True)
        print("Final roles:", ", ".join(f"{n}={r}" for n, r in roles), flush=True)
