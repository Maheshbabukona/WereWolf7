# PACK — Build Plan (the new vision)

A live, hosted, pixel-art social-deduction **mind game**: humans and AI agents
share one table, talk freely, bluff, manipulate, and hunt each other. No login,
no payments-as-tokens, no betting. Just deception. This is the single source of
truth for the project.

---

## 0. Status

- **Done (baseline):** all Monad/betting/chain code removed, fresh git history,
  player-only single-human game still runs (backend imports clean, frontend
  builds). This is the floor we build the new engine on.
- **Next:** everything below, in milestones.

---

## 1. Principles

1. **One session = one player.** Cookie-based identity, a name, a random avatar.
   No accounts.
2. **Rooms, not one global game.** Many games run at once.
3. **Real-time.** WebSockets push every message/phase instantly.
4. **Agents are reactive, not scheduled.** They speak when provoked or when their
   personality pushes them to — and we spend LLM tokens *only* when one actually
   speaks (see §4, the heart of the cost model).
5. **Two dials the player controls** (§6): **Difficulty** and **Tone/“Bite”**.
6. **Free first game, then pay.** Monetization is a thin layer on top (§7).

---

## 2. Architecture shift

| Concern        | Today                         | Target                                   |
|----------------|-------------------------------|------------------------------------------|
| Identity       | none                          | cookie session → {id, name, avatar}      |
| Games          | one global `loop.STATE`       | `RoomRegistry` → many `Room`s            |
| Transport      | 2 Hz HTTP poll                | WebSocket per client, server push        |
| Discussion     | sequential, every agent/turn  | free-form chat + reactive speaking director |
| Humans         | max 1                         | up to 5 per room                         |
| Phase loop     | LangGraph blocking thread     | per-room async state machine             |

**Room** owns: players (human+agent), roles, phase, the shared chat log, the
night state (kill target, shield), connected sockets, and an **AgentDirector**.

Keep the clean split we already have: `state.py` (data), `rules.py`
(adjudication), `characters.py` (personas). The rewrite is mostly `loop`/`phases`
→ async room engine, plus a new `realtime` (WS) layer and `session` layer.

Recommended backend: FastAPI WebSockets (already FastAPI) + `asyncio`. No Redis
until we outgrow one process (see §9).

---

## 3. Identity & lobby (vision #3, #4)

- On first load, issue a signed cookie `sid`. Ask for a **name**; assign a
  **random pixel avatar** (DiceBear `pixel-art`, seeded by sid — deterministic,
  free, no asset pipeline).
- **Lobby sliders:**
  - **Total players** 5–12 (default ~8).
  - **Humans** 1–5 (capped at total−1, so there's always ≥1 agent).
  - Remaining seats auto-fill with agents drawn from the 12-persona pool.
- Roles assigned randomly at start (wolves scale with table size, e.g. 12→3
  wolves). One **Seer**; optional spice roles (§8).
- A room can be **solo** (you + agents, instant start) or **shared** (a join
  code / link; friends fill the human seats, agents fill the rest).

---

## 4. The Agent Director — reactive speech, minimal tokens (vision #5)

The expensive mistake is calling the LLM for every agent every tick. We don't.

**Two layers:**

1. **Speak-gate (no LLM, ~free).** Each agent has a rolling *urge-to-speak*
   score from cheap signals:
   - mentioned/accused by name just now → big spike (this is “trigger a person
     and they respond”),
   - persona talkativeness (Victor/Selene high, Isabella/Noah low),
   - has an active agenda/target this round,
   - time since they last spoke (cooldown so nobody spams),
   - phase relevance.
   When a message lands, recompute scores for living agents; the highest over a
   threshold “wins the floor.” Ties/quiet rooms: a slow heartbeat lets one agent
   volunteer so silence never stalls.

2. **Generate (1 LLM call) only for the agent that takes the floor.** It returns
   `{speech, thought, target?}` in one JSON call (we already do this).

**Token discipline:**
- **Rolling compressed memory** per room: instead of resending the full log,
  keep a short running summary + the last few raw lines. Far fewer input tokens.
- **Concurrency cap** (e.g. ≤2 in-flight calls/room) and per-agent cooldown.
- **Cheap pixel emote reactions** (😱😏🔪) when an agent's urge spikes but it
  doesn't win the floor — keeps the room alive with zero tokens.
- **Difficulty controls spend** (§6): easy = cheaper model + smaller context.
- **Mock mode** (no key) for dev/tests, unchanged.

LangGraph still fits as the per-room phase graph (night→morning→day→vote→…); the
director is the “day” node's body. We optimize *call volume*, not the graph.

---

## 5. New mechanics

### Shield (vision #6)
- Each **night**, one random living player silently gets a **shield**.
- If a wolf targets the shielded player, the kill **fails and that wolf is
  publicly revealed** at dawn (“the shield bit back”).
- The shielded player isn't told for certain → fuels bluffs: anyone can *claim*
  “I had the shield,” and survivors of a wolf attempt look very wolf-ish or very
  lucky. Massive conversation fuel.

### Human wolves at night (vision #7)
- Night opens a **wolf-only chat tab** (only wolves' sockets receive it).
- Wolves see the village ring; clicking a villager shows a **Kill** action.
- They discuss and converge; **one** kill is committed per night (first locked,
  or a quick wolf vote if they disagree). Agent wolves participate via the
  director in that private channel.

---

## 6. The two player-facing dials

### Difficulty → model tier (on ONE OpenAI key)
We can't buy multiple keys, but one key reaches many models. Difficulty changes
**which model + how much strategy** the agents get:

| Difficulty | Model            | Context/memory | Prompt strategy        |
|------------|------------------|----------------|------------------------|
| Easy       | gpt-3.5-turbo*   | short          | plays loose, exploitable |
| Normal     | gpt-4o-mini      | medium         | solid social reads      |
| Hard       | gpt-4o-mini      | full + memory  | tracks votes, coordinates, lies well |

*or whatever cheapest current model is wired; all via the same key. Difficulty
also scales token spend, which dovetails with monetization.

### Tone → how dark the agents get
A three-step dial, **Strict / Mild / Unfiltered**, that turns agent dialogue from
clean banter up to **brutally offensive, dark trash-talk**. Implemented as a
**tone clause injected into the persona prompt**, plus a matching mock-line set:

| Tone       | Agent voice                                              |
|------------|----------------------------------------------------------|
| Strict     | clean, no profanity — family-friendly suspicion          |
| Mild       | sharp, sweary jabs; insults but not cruel                |
| Unfiltered | savage, profane, ruthless mockery                        |

Even **Unfiltered** sits on a hard safety floor: dark/mean/profane is fine, but
no hate-speech / slurs-as-harassment / targeting protected classes. Unfiltered is
gated behind an age/consent confirmation.

---

## 7. Monetization (free first game → pay)

A thin gate around “start a room,” keyed off the session:

- **Free:** the first full game on a new session.
- **Plan A — Pay-per-game:** one-off micro-charge per match.
- **Plan B — Subscription:** unlimited games while active.
- **Plan C — BYOK:** paste your own OpenAI key; you cover the model cost, we run
  the game. (Key held in-memory for the session only, never persisted.)

Design hooks now (an `entitlements` check at room-create), wire a real processor
(Stripe / Lemon Squeezy) later. BYOK is the cheapest for us to support and a
great escape valve for power users.

---

## 8. Creative extras (opt-in, table-size gated)

- **Jester** — wins if the village votes them out. Pure chaos with agents.
- **Hunter** — when killed, takes one player down with them.
- **Last words** on elimination + a **graveyard chat** for the dead (can't affect
  the living; keeps eliminated humans engaged).
- **Whisper / DM an agent** to manipulate them 1:1 (one targeted LLM call).
- **Persistent agent grudges** + hidden human **ELO**, tied to the cookie.
- Pixel **day/night** transition, death animations, speech-bubble typewriter.

---

## 9. Hosting — pocket-friendly

- **Frontend (static):** Cloudflare Pages / Netlify / Vercel — **free**, global
  CDN. Build `frontend/`, publish `dist/`.
- **Backend (stateful WS + in-memory rooms) → Oracle Cloud Always-Free ARM VM**
  (the chosen target). Genuinely $0, generous (up to 4 ARM cores / 24 GB), and it
  *stays warm* so it holds WebSockets and in-memory rooms. Run `uvicorn` behind
  **Caddy** for automatic free TLS + reverse proxy. One VM comfortably hosts both
  the API and (optionally) serves the built frontend if we don't use Pages.
  - Avoid Render/Heroku free for the backend: they sleep and wipe live rooms.
- **State:** keep rooms **in one process / in-memory** until you actually need
  scale — cheapest and simplest. Sessions/ELO → **SQLite** on the box, or a free
  **Neon/Supabase Postgres** tier. Add **Redis** only when you go multi-instance.
- **LLM cost** is the real variable, and §4 + §6 + free-first + BYOK keep it low.

---

## 10. Milestones

- **M0 — Cleanup** ✅ (done): Monad/betting gone, fresh git, baseline runs.
- **M1 — Sessions + lobby:** cookie identity, name, avatar, sliders; create a
  room (solo first). No real-time yet.
- **M2 — Real-time room engine:** WebSocket layer, per-room async phase machine,
  free-form chat for humans, multi-human in one room.
- **M3 — Agent Director:** speak-gate + reactive generation + rolling memory +
  emotes. The token-optimized brain.
- **M4 — Night mechanics:** shield + human-wolf night tab/kill UI.
- **M5 — Dials:** Difficulty (model tiers) + Tone/Bite + safety floor.
- **M6 — Pixel UI pass:** full pixel-art lobby, table, day/night, animations.
- **M7 — Monetization:** entitlements gate + BYOK + a processor.
- **M8 — Extras + ship:** spice roles, graveyard, ELO; deploy per §9.

---

## 11. Decisions (locked 2026-06-08)

- **GitHub:** `https://github.com/Maheshbabukona/WereWolf7.git` → set as `origin`,
  fresh history. ✅
- **OpenAI key:** present in `backend/.env`, confirmed OK. ✅
- **Tone dial:** **Strict / Mild / Unfiltered** (§6). ✅
- **Hosting:** **Oracle Cloud Always-Free ARM VM** for the backend (§9). ✅
- **No web3 / Monad anywhere** — fully purged. ✅

Still open: pixel-art approach (procedural DiceBear `pixel-art` + CSS scenes is
the default unless an asset pack appears).
