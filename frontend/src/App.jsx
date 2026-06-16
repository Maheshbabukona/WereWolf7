import { useEffect, useState } from "react";
import { fetchState, startGame, quitGame } from "./api";
import TopBar from "./scene/TopBar";
import Lobby from "./scene/Lobby";
import VillageScene from "./scene/VillageScene";
import DialogueOverlay from "./scene/DialogueOverlay";
import GameOverOverlay from "./scene/GameOverOverlay";
import PlayPanel from "./play/PlayPanel";
import "./styles.css";

export default function App() {
  // screen: null (checking) | "lobby" | "play"
  const [screen, setScreen] = useState(null);
  const [state, setState] = useState(null);
  const [err, setErr] = useState(null);

  // On load, auto-rejoin a game already in progress (survives a reload) —
  // otherwise show the lobby.
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const s = await fetchState("player");
        if (!active) return;
        if (s && s.phase && s.phase !== "idle" && s.you) { setState(s); setScreen("play"); }
        else setScreen("lobby");
      } catch { if (active) setScreen("lobby"); }
    })();
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (screen !== "play") return undefined;
    let active = true;
    const tick = async () => {
      try {
        const s = await fetchState("player");
        if (active) { setState(s); setErr(null); }
      } catch (e) {
        if (active) setErr(e.message);
      }
    };
    tick();
    const id = setInterval(tick, 500);
    return () => { active = false; clearInterval(id); };
  }, [screen]);

  // Lobby calls this. If a game is already running, rejoin it instead of erroring.
  const begin = async (totalPlayers) => {
    const res = await startGame(totalPlayers);
    if (res && res.ok === false) {
      if ((res.reason || "").includes("in progress")) { setScreen("play"); return res; }
      return res;
    }
    setState(null);
    setScreen("play");
    return res;
  };

  const newGame = async () => begin(state?.players?.length || 8);
  const goHome = async () => {
    try { await quitGame(); } catch { /* ignore */ }
    setScreen("lobby"); setState(null);
  };

  if (screen === null) {
    return (
      <div className="lobby"><div className="lobby-card">
        <h1 className="home-title">🐺 PACK</h1>
        <p className="home-sub">Reconnecting…</p>
      </div></div>
    );
  }
  if (screen === "lobby") {
    return <Lobby onEnter={begin} />;
  }

  const phase = state?.phase ?? "idle";
  const isNight = phase === "night" || phase === "setup";
  const playing = phase !== "idle";

  return (
    <div className={`app ${isNight ? "night" : "day"} player`}>
      <TopBar state={state} onExit={goHome} />
      {err && <div className="err-banner">⚠ Can't reach backend ({err}). Is uvicorn running on :8000?</div>}

      <div className="main">
        <div className="stage">
          <VillageScene state={state} />
          {playing && <DialogueOverlay state={state} />}
          {isNight && playing && <div className="night-toast">🌙 The village sleeps…</div>}
          {playing && state?.nightResult && phase === "morning" && (
            <div className="result-toast">☀️ <b>{state.nightResult.victimName}</b> was found dead at dawn.</div>
          )}
          {playing && state?.dayResult && (
            <div className="result-toast vote">
              {state.dayResult.name
                ? <>🗳️ The village voted out <b>{state.dayResult.name}</b> — they were a <b>{state.dayResult.role}</b>.</>
                : <>🗳️ The village couldn't agree — nobody was voted out.</>}
            </div>
          )}
        </div>
        {playing && (
          <aside className="sidebar">
            <PlayPanel state={state} />
          </aside>
        )}
      </div>

      <GameOverOverlay state={state} onNewGame={newGame} onHome={goHome} />
    </div>
  );
}
