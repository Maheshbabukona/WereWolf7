const BASE =
  import.meta.env.VITE_BACKEND_URL ||
  "http://localhost:8000";

// --- session identity (no login) ---
// The client holds a session id in localStorage and echoes it on every request.
// (Swappable for an httpOnly cookie when hosted; see docs/PLAN.md §3.)
const SID_KEY = "pack_sid";
const getSid = () => localStorage.getItem(SID_KEY);
const setSid = (s) => { if (s) localStorage.setItem(SID_KEY, s); };

function headers(extra = {}) {
  const h = { ...extra };
  const s = getSid();
  if (s) h["X-Session-Id"] = s;
  return h;
}

export async function getSession() {
  const r = await fetch(`${BASE}/session`, { headers: headers() });
  if (!r.ok) throw new Error(`session ${r.status}`);
  const j = await r.json();
  setSid(j.sid);
  return j;
}

export async function saveSession(name, avatar, theme, scene) {
  const r = await fetch(`${BASE}/session`, {
    method: "POST",
    headers: headers({ "Content-Type": "application/json" }),
    body: JSON.stringify({ name, avatar, theme, scene }),
  });
  if (!r.ok) throw new Error(`session ${r.status}`);
  const j = await r.json();
  setSid(j.sid);
  return j;
}

export async function fetchState(mode) {
  const r = await fetch(`${BASE}/state?mode=${mode}`, { headers: headers() });
  if (!r.ok) throw new Error(`state ${r.status}`);
  return r.json();
}

export async function startGame(totalPlayers) {
  const r = await fetch(`${BASE}/control/start`, {
    method: "POST",
    headers: headers({ "Content-Type": "application/json" }),
    body: JSON.stringify({ totalPlayers }),
  });
  return r.json();
}

// Raise a hand — ask the Director for the floor.
export async function raiseHand() {
  return fetch(`${BASE}/control/raise`, { method: "POST", headers: headers() });
}

// Submit your line once the Director hands you the floor.
export async function sendSpeech(text) {
  return fetch(`${BASE}/control/say`, {
    method: "POST",
    headers: headers({ "Content-Type": "application/json" }),
    body: JSON.stringify({ text }),
  });
}

// Set/clear your SECRET vote (hidden from everyone; "" clears).
export async function sendVote(target) {
  return fetch(`${BASE}/control/vote`, {
    method: "POST",
    headers: headers({ "Content-Type": "application/json" }),
    body: JSON.stringify({ target }),
  });
}

// Night choice — seer investigation target or wolf kill pick.
export async function sendNight(target) {
  return fetch(`${BASE}/control/night`, {
    method: "POST",
    headers: headers({ "Content-Type": "application/json" }),
    body: JSON.stringify({ target }),
  });
}

// Leave the current game (abort it so a new one can start).
export async function quitGame() {
  return fetch(`${BASE}/control/quit`, { method: "POST", headers: headers() });
}
