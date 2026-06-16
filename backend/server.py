"""FastAPI HTTP layer — routes only.

Thin by design: it starts a game in a background thread and serializes state.
All game logic lives in the `game` package. Run:
    uvicorn server:app --reload --port 8000
"""
import threading

from fastapi import FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from game import history, human, livestate, loop, serialize, session
from game.roster import MAX_PLAYERS, MIN_PLAYERS, new_game
from game.themes import DEFAULT_THEME, THEMES


class SayIn(BaseModel):
    text: str


class VoteIn(BaseModel):
    target: str


class SessionIn(BaseModel):
    name: str
    avatar: str
    theme: str = DEFAULT_THEME
    scene: str = "scene1"


class StartIn(BaseModel):
    totalPlayers: int = 7


app = FastAPI(title="Pack — Agent Werewolf")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Session-Id"],
)

_lock = threading.Lock()
# Monotonic game-id counter. Seeded from history on first use, then incremented
# in-process so back-to-back games never collide (history is written only at
# game end, so reading the file per-start could reuse an id).
_next_id: int | None = None


@app.on_event("startup")
def _restore_live_game():
    """On boot, restore the last live game from disk. If it wasn't finished,
    resume it from the next phase so a backend restart doesn't lose the match."""
    snap = livestate.load()
    if snap is None:
        return
    loop.STATE = snap
    if snap.phase != "ended":
        print(f"[startup] resuming game {snap.game_id} from phase '{snap.phase}'")
        threading.Thread(target=loop.resume_game, args=(snap,), daemon=True).start()


@app.get("/health")
def health():
    return {"ok": True}


# ---- session identity (no login) ------------------------------------------ #

@app.get("/session")
def get_session(x_session_id: str | None = Header(default=None)):
    """Return the caller's session + the theme catalog (scenes + characters per
    theme) the lobby needs. Mints a new id if they don't have one yet; the client
    persists the returned sid and sends it back as X-Session-Id."""
    data = session.get(x_session_id) or {}
    sid = x_session_id or session.new_sid()
    return {
        "sid": sid,
        "name": data.get("name"),
        "avatar": data.get("avatar"),
        "theme": data.get("theme", DEFAULT_THEME),
        "scene": data.get("scene", "scene1"),
        "themes": THEMES,
        "limits": {"min": MIN_PLAYERS, "max": MAX_PLAYERS},
    }


@app.post("/session")
def set_session(body: SessionIn, x_session_id: str | None = Header(default=None)):
    sid = x_session_id or session.new_sid()
    data = session.save(sid, body.name, body.avatar, body.theme, body.scene)
    return {"sid": sid, **data}


# ---- game control --------------------------------------------------------- #

@app.post("/control/start")
def start(body: StartIn, x_session_id: str | None = Header(default=None)):
    """Start a fresh game sized by the lobby. The human seat uses the session's
    name + avatar. (Single-human for now; multi-human rooms arrive in M2.)"""
    global _next_id
    me = session.get(x_session_id)
    if not me:
        return {"ok": False, "reason": "no session — set your name + avatar first"}
    with _lock:
        running = loop.STATE is not None and loop.STATE.phase not in ("ended", "idle")
        if running:
            return {"ok": False, "reason": "game in progress", "gameId": loop.STATE.game_id}
        if _next_id is None:
            _next_id = history.next_game_id()
        gid = _next_id
        _next_id += 1
        state = new_game(gid, total_players=body.totalPlayers, human=me)
        threading.Thread(target=loop.run_game, args=(state,), daemon=True).start()
    return {"ok": True, "gameId": state.game_id, "totalPlayers": len(state.players)}


@app.post("/control/raise")
def control_raise():
    """Human raises a hand — the Director gives them the floor at the next beat."""
    human.raise_hand()
    return {"ok": True}


@app.post("/control/say")
def control_say(body: SayIn):
    """Human's line once the Director has handed them the floor."""
    human.submit(body.text)
    return {"ok": True}


@app.post("/control/vote")
def control_vote(body: VoteIn):
    """Human sets/changes their SECRET vote at any time ("" clears it)."""
    human.set_vote(body.target)
    return {"ok": True}


@app.post("/control/night")
def control_night(body: VoteIn):
    """Human's night choice — seer investigation target or wolf kill pick."""
    human.set_night_action(body.target)
    return {"ok": True}


@app.post("/control/quit")
def control_quit():
    """Human leaves the game — abort the current match so a new one can start."""
    if loop.STATE is not None and loop.STATE.phase not in ("ended", "idle"):
        loop.STATE.aborted = True
    return {"ok": True}


@app.get("/state")
def get_state(mode: str = "player"):
    state = loop.STATE
    if state is None:
        return {"phase": "idle"}
    mode = mode if mode in ("god", "player") else "player"
    return serialize.to_client(state, mode)


@app.get("/history")
def get_history():
    """Past completed games, newest first."""
    return list(reversed(history.load()))
