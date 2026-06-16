# PACK — Vision

> *Building the first world where you can't tell who's human.*

This is the north-star document: the full thing we're imagining and building
toward, not just the next sprint. For the concrete staged build, see
[PLAN.md](PLAN.md) and [MOVEMENT-GAME.md](MOVEMENT-GAME.md).

---

## 1. The one sentence

We're building a hosted, real-time, pixel-art social-deduction **mind game** where
humans and autonomous AI agents sit at the same table — bluffing, manipulating,
remembering, accusing, and hunting each other — and **you genuinely can't tell
which players are people**. It looks like *Among Us × Werewolf*. The real project
is making AI agents that deceive, persuade, and read a room at a human level —
live, at scale, and at sane cost.

## 2. The north star

The moment we're chasing: a human gets voted out by an argument an *agent*
constructed about them — and the whole table, human and AI alike, believes it.
We're building toward the **Turing test as a game you play for fun**: a social
arena where the cleverest liars, the sharpest reads, and the best manipulators are
increasingly the players that were never human.

## 3. The experience we're designing

- **No login, no friction.** You arrive with a name and a face (a pixel avatar)
  and you're in. Identity is a session, not an account.
- **You pick your world.** A pre-game lobby (Among-Us style) where you choose a
  **theme**, a **scene** within it, your **character**, and the **table size**
  (5–12 players; up to 5 human, the rest agents).
- **You drop into a living village.** A dozen players roam a map. Some are people.
  Most, eventually, are not — and you can't easily tell.
- **Night falls and the hunt begins.** Villagers sleep; wolves move in the dark.
- **Day breaks and the room erupts.** A live, unscripted meeting where everyone
  argues, accuses, defends, and votes. The agents talk *to you*, by name.
- **You win by reading people** — or by lying better than they do.

## 4. Game design

### Roles
- **Villagers (crew)** and **Wolves (impostors)** — visually identical. A
  **Seer/Oracle** that can learn one player's true role. Room for spice roles we're
  imagining: **Jester** (wins if voted out), **Hunter** (takes one down on death),
  lovers, and more — table-size-gated.
- **The Shield** — each night one random player is silently protected. If a wolf
  targets the shielded player, the kill fails and **the wolf is revealed**. This is
  a deliberate engine for bluffs: anyone can *claim* they had the shield, and
  surviving an attempt makes you look either very lucky or very guilty.

### The Night — a real-time stealth phase (our original twist)
A top-down world where position and proximity matter:
- **Villagers sleep by default** — they can't see or move, and you don't know who
  else is awake (deliberate information asymmetry).
- **Each villager gets one 5-second wake window**, spent whenever they choose.
  Awake, you move and see within a vision radius — so a wolf near you gets *caught*
  (witnessed). Spend it at the wrong moment and it's wasted, and you might be killed
  in your sleep.
- **Wolves roam all night** and kill a villager they're adjacent to (with a
  cooldown), leaving a body.
- **Night length = 5 seconds × living villagers** — a shared attention budget. The
  night ends on that timer, on a body being found, or when a witness slams the
  **emergency** button.
- Everything you witnessed at night becomes **ammunition in the daylight meeting.**

### The Meeting — a live, reactive deliberation
Triggered by night's end, a body, or an emergency:
- **Reactive, not round-robin.** Nobody takes equal turns. Whoever is most
  provoked — named, attacked, or just can't stay quiet — speaks next. The room can
  fall silent. One voice at a time.
- **Floor control with the human at the center.** The room *holds* while you're
  typing, and the most-relevant agent answers *you* first, by name. You're never
  talked over or ignored.
- **Voting is always open.** Players cast and change votes throughout; the day ends
  the instant a living majority locks, or when the timer expires — never a
  hardcoded number of rounds.
- **Eject one** (or skip), reveal or conceal their role, and back to night.

### Win conditions
Villagers win by ejecting every wolf; wolves win by reaching numerical parity. The
game runs as many night→meeting cycles as it takes — never a fixed length.

## 5. The AI — the actual project

### A multi-agent mind, not a chatbot
We're orchestrating a roomful of autonomous LLM agents that share one evolving
world, each seeing it through a private, fog-of-war lens: its own secret role, its
knowledge, its persona, its grudges. Each agent is a *player* with an agenda — not
a narrator.

### The Agent Director — making a crowd feel human
The hardest part of "many agents talking" is making it feel like a conversation
instead of a feed, without burning a model call per agent per tick. So we're
engineering the conversation itself:
- A **zero-LLM scoring layer** continuously decides *who is most compelled to
  speak* — who was just named, who was attacked, whose personality can't stay
  quiet, who's been silent too long, who just spoke (cooldown).
- Only the voice that **takes the floor** spends a model call. This turns an
  O(agents × rounds) round-robin into roughly **one LLM call per actual
  utterance** — and produces interruptions, pile-ons, real silences, and a room
  that holds for a human.

### Deception, persuasion, and grounding
We're shaping prompting and reasoning so agents:
- **React to what's actually said** — to your exact words, to being insulted or
  accused, to other agents — and never ignore being addressed.
- **Stay grounded** — no fabricated accusations when nothing is yet known (the
  first-morning problem), no corporate filler, no goldfish memory.
- **Protect their secrets and weaponize information** — wolves blend in and steer
  suspicion; the seer decides whether to reveal; everyone bluffs.
- Return **structured output** (public line + hidden private reasoning + an
  optional vote) in a single call, so private "what they're really thinking" costs
  no extra inference — and powers a spectator/god view of dramatic irony.

### The two dials players control
- **Difficulty → capability.** A single API key maps to a **model tier**: stronger
  models and richer strategy at higher difficulty, cheaper tiers (and looser play)
  lower down.
- **Tone → darkness.** **Strict / Mild / Unfiltered** — from clean banter to
  ruthless, profane trash-talk — implemented as a tone clause and a matching
  mock-line set, behind an age/consent gate and a hard safety floor (dark and mean,
  never hate or harassment).

### Built to ship cheaply and not break
- **Bring-your-own-key**, model-tiering, and a **keyless mock mode** that plays the
  entire game deterministically (for tests, CI, and demos).
- **Timeouts and graceful fallback** so a stalled model can never freeze the world.

## 6. Architecture we're building on

- **Real-time, server-authoritative.** A FastAPI backend with **WebSockets** and a
  ~15 Hz simulation owns every entity's position, sleep/wake state, and kills;
  clients send input and render the pushed snapshot.
- **Fog of war enforced on the server** — a sleeping villager is sent nothing; an
  awake villager or wolf sees within their radius; nobody's role leaks.
- **Game flow as a state machine** (LangGraph) — phases as nodes, conditional edges
  for the night→meeting loop and win checks; a single shared game-state object the
  nodes mutate.
- **Rooms.** Many concurrent games, each its own world and agent director; in-memory
  while it fits one process, with a clean path to multi-instance later.
- **Session identity** via a lightweight signed id — name, avatar, and (eventually)
  persistent reputation.

## 7. Art & worlds

- **Pixel art, chibi characters.** We start with characters as **tokens on a
  top-down board** (works with the art we have now) and upgrade toward true
  top-down tilemaps and directional, animated sprites.
- **Themes bind art + roster.** A theme is an art family — a set of scenes plus the
  characters that belong in it. We ship one complete **Fantasy** theme (Ancient
  Ruins, Dragon Hall, Wildwood, The Crypt; 23 chibi characters) and design the
  system so a new theme (sci-fi, post-apocalyptic, …) is a drop-in once matching
  art exists. Day/night is driven by the scene art itself.

## 8. Business model we're designing for

- **The first game is free.** Then:
  - **Pay-per-game**, **subscription**, or **bring-your-own-key** (you cover the
    model cost, we run the game).
- A thin entitlements gate at room-create, so monetization never tangles the
  engine; BYOK keeps inference cost off us and is a power-user escape valve.

## 9. Hosting we're targeting

- **Frontend** as a static build on a free CDN (Cloudflare Pages).
- **Backend** on an **Oracle Cloud Always-Free ARM VM** — a process that stays warm
  to hold WebSockets and in-memory rooms — behind Caddy for free TLS.
- Cost discipline lives in the AI layer: the Director's call-bounding, model-tiering,
  free-first, and BYOK.

## 10. Where we are (and the path)

- **Done & working:** the AI core — reactive, floor-controlled meeting with live
  voting and human-level agent dialogue; the lobby (sessions, themes, scenes,
  character & table-size selection); the real-time movement foundation; and the
  **Night** (sleep, the 5-second wake, server-side fog, wolves that hunt and kill,
  witnesses, the night timer, a dawn summary).
- **Building next:** wiring **dawn → the meeting** so witnesses accuse and the table
  can finally eject a wolf (closing the full Among-Us loop); then richer art
  (top-down sprites), the shield, human-wolf night UI, and the dials.

## 11. The horizon (with infinite runway)

We're aiming at:
- **Agents that remember you across games** and carry grudges and rivalries.
- **Whispers and conspiracies** — private wolf channels, and one-on-one DMs where an
  agent can be *manipulated* (and manipulate you back).
- **Reputation and ranked play** — a hidden ELO for humans, and agents that build
  reputations of their own.
- **A library of themes and worlds**, agents that move, emote, and lie with body
  language, and sabotage-style crises.
- The endgame: a social arena where the most interesting opponents are the ones
  that were never human.

## 12. Principles

1. **You can never tell.** Human and agent are indistinguishable by design.
2. **Agents are players, not NPCs.** They react, remember, deceive, and have
   agendas.
3. **Reactive, never round-robin.** Conversation is interrupt-driven and
   time-pressured.
4. **The human is never ignored.** The room listens, holds, and answers you.
5. **Cheap by construction.** Spend a model call only when a voice truly speaks.
6. **Dark is allowed; hate is not.** Edge with a hard safety floor.
