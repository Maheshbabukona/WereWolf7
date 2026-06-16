# PACK → "Among Us with agents" (movement game) — research & build plan

The game is pivoting from a ring-discussion game to a **spatial, real-time
movement game**. The reactive discussion + live voting we just built is NOT
thrown away — it becomes the **MEETING**. This doc is the research + the staged
build path.

## The loop (Among Us, mapped to us)

    NIGHT (spatial, real-time)  →  MEETING (discuss + vote, eject)  →  repeat
                                                                        until a faction wins

- **Roles:** Villagers (crew) vs Wolves (impostors) — visually identical.
- **Win:** villagers eject all wolves; wolves reach numerical parity.

## NIGHT — your sleep/wake mechanic (the new, spatial phase)

A top-down map; every player has a position.

- **Villagers SLEEP by default** — can't move or see, shown lying down. You don't
  know who else is awake (info asymmetry).
- **One wake window, 5s,** per villager — spend it ONCE, whenever you choose.
  While awake you can move/look and you **see anyone within your vision radius**,
  so a wolf near you gets caught. Spend it at the wrong moment and it's wasted
  (and you might be killed while asleep).
- **Wolves ROAM** all night and **kill a villager they're adjacent to** (with a
  cooldown). A kill leaves a **body**.
- **Night length = 5s × (number of villagers)** — a shared "attention budget".
  Night ends when that elapses, when a **body is found**, or when an awake
  villager hits **EMERGENCY**.
- **Agents:** wolf-agents path toward isolated sleepers and strike while avoiding
  awake villagers; villager-agents pick when to spend their wake (timing/suspicion
  heuristics) and remember what they saw. All movement AI is cheap (no LLM).

## MEETING — already built

Triggered by night end / body found / emergency. The reactive discussion + live
voting engine runs; **what witnesses saw at night feeds their prompts** ("I woke
and saw Victor by the body"). The table ejects one player (or skips), then back
to NIGHT.

## Architecture

- **Real-time → WebSockets**, server-authoritative tick (~15 Hz). Server owns
  positions/sleep/kills; clients send input (movement, wake, kill, emergency) and
  render the pushed snapshot. (This is the M2 real-time foundation — now required.)
- **Movement layer = new. Meeting layer = existing.** The game loop alternates.
- **Agent movement AI = cheap heuristics/pathfinding** (no tokens). LLM is spent
  only in meetings, as today.

## The asset reality (the one real blocker)

Our art is **side-view** (parallax backgrounds + front-facing chibi sprites).
Among Us is **top-down**. Two visual paths:

- **(A) True top-down** — a tilemap + 4-direction character sheets. Authentic
  Among-Us look, but needs NEW top-down art we don't have yet.
- **(B) "Tokens on a board"** — the chibi sprites as pieces that slide around a
  stylized top-down map we build from simple tiles/shapes. **Works with the art we
  have right now**, so we can build immediately; upgrade to (A) later if you get
  top-down art.

## Build iterations

1. **Movement foundation** — WebSocket room; a map; you move your character
   (WASD/arrows) in real time; agents wander; live position sync; proximity
   highlight. *Playable, visible.*
2. **Sleep/wake + vision** — villagers asleep; the 5s wake; vision radius; the
   `5s × villagers` night timer.
3. **Kill + bodies + emergency** — wolves kill adjacent sleepers; bodies; report/
   emergency triggers the meeting.
4. **Meeting integration** — night observations feed the discussion; eject; loop
   to a faction win.
5. **Polish** — animations, sabotage-style events, sound, etc.
