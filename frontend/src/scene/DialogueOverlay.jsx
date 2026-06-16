import { useEffect, useState } from "react";

// The center-stage transcript viewer (JRPG style). Shows one line at a time with
// the speaker's portrait. It FOLLOWS the live discussion by default; ◀ ▶ step
// through history (it freezes on the line you pick), and "⤓ Live" snaps back —
// so browsing the past is opt-in and you never get stuck.
const COLORS = ["#ef4444", "#3b82f6", "#22c55e", "#f472b6", "#f59e0b", "#a855f7", "#06b6d4"];
const FACES = ["🧑‍🦰", "🧑‍🦱", "🧔", "🧑‍🦳", "👱", "🧑‍🎤", "🧓"];

function latestThought(reasoning, name) {
  for (let i = (reasoning?.length ?? 0) - 1; i >= 0; i--) {
    const r = reasoning[i];
    if (r.speaker !== name) continue;
    const t = r.thought || "";
    if (t.startsWith("(night)") || t.startsWith("(vote)")) continue;
    return t;
  }
  return null;
}

function useTypewriter(text, cps = 34) {
  const [n, setN] = useState(0);
  useEffect(() => {
    setN(0);
    if (!text) return undefined;
    const id = setInterval(() => setN((x) => (x >= text.length ? x : x + 1)), 1000 / cps);
    return () => clearInterval(id);
  }, [text, cps]);
  return { shown: text ? text.slice(0, n) : "", done: !text || n >= text.length };
}

export default function DialogueOverlay({ state, godMode }) {
  const log = state?.discussionLog || [];
  const last = log.length - 1;
  const [viewIdx, setViewIdx] = useState(null); // null = follow live (latest)
  const [stage, setStage] = useState(0);        // avatar fallback: 0 sprite,1 dicebear,2 emoji

  const live = viewIdx === null || viewIdx >= last;
  const idx = live ? last : viewIdx;
  const entry = idx >= 0 ? log[idx] : null;

  // Typewriter only on the live latest line; past lines show in full.
  const { shown, done } = useTypewriter(live ? entry?.text || "" : "");
  // Reset the avatar fallback whenever the shown speaker changes.
  useEffect(() => { setStage(0); }, [entry?.speaker]);

  if (!entry) return null;

  const player = state.players?.find((p) => p.name === entry.speaker);
  const color = player ? COLORS[player.idx % COLORS.length] : "#888";
  const seed = encodeURIComponent(entry.speaker);
  const sprite = player?.avatar ? `/avatars/${player.avatar}.png` : null;
  const avatar = stage === 0 && sprite ? sprite : `https://api.dicebear.com/9.x/pixel-art/svg?seed=${seed}`;
  const text = live ? shown : entry.text;
  const thought = live && godMode ? latestThought(state.privateReasoning, entry.speaker) : null;

  const goPrev = () => setViewIdx(Math.max(0, idx - 1));
  const goNext = () => { const n = idx + 1; setViewIdx(n >= last ? null : n); };

  return (
    <div className="dialogue-overlay">
      <div className="dlg-portrait" style={{ "--c": color }}>
        {stage < 2 ? (
          <img src={avatar} alt={entry.speaker} onError={() => setStage((s) => s + 1)} />
        ) : (
          <span className="dlg-face">{FACES[(player?.idx ?? 0) % FACES.length]}</span>
        )}
      </div>
      <div className="dlg-box">
        <div className="dlg-head">
          <span className="dlg-name">✦ {entry.speaker} ✦</span>
          <span className="dlg-nav">
            <button className="dlg-arrow" onClick={goPrev} disabled={idx <= 0}>◀</button>
            <span className="dlg-count">{idx + 1}/{log.length}</span>
            <button className="dlg-arrow" onClick={goNext} disabled={live}>▶</button>
            {live
              ? <span className="dlg-live">● LIVE</span>
              : <button className="dlg-arrow live" onClick={() => setViewIdx(null)}>⤓ Live</button>}
          </span>
        </div>
        <div className="dlg-text">{text}{live && !done && <span className="dlg-caret">▌</span>}</div>
        {done && thought && <div className="dlg-thought">💭 {thought}</div>}
      </div>
    </div>
  );
}
