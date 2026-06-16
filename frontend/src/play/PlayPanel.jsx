import { useState } from "react";
import { raiseHand, sendSpeech, sendVote, sendNight } from "../api";

const ROLE_EMOJI = { wolf: "🐺", seer: "🔮", villager: "🧑‍🌾" };

// The human's control panel. Derives the controls each ROLE needs:
//  - everyone (day): raise hand to speak, secret vote (cast/change/clear)
//  - seer (night): investigate one player
//  - wolf (night): see partner + wolf chat, vote the kill
//  - villager (night): sleep
export default function PlayPanel({ state }) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const you = state?.you;
  const awaiting = state?.awaiting;
  if (!you) return null;

  const me = state.players?.find((p) => p.idx === you.idx);
  const dead = me && !me.alive;
  const phase = state.phase;
  const isDay = phase === "day";
  const isNight = phase === "night";
  const haveFloor = awaiting?.kind === "speak" && awaiting.playerIdx === you.idx;
  const secsLeft = state.daySecondsLeft;
  const others = (state.players || []).filter((p) => p.alive && p.idx !== you.idx);
  const nameOf = (n) => n.split(" ")[0];

  const submit = async () => {
    if (!text.trim()) return;
    setBusy(true);
    try { await sendSpeech(text); setText(""); } finally { setBusy(false); }
  };
  const ask = async () => { try { await raiseHand(); } catch { /* ignore */ } };
  const vote = async (name) => {
    try { await sendVote(you.vote === name ? "" : name); } catch { /* ignore */ }
  };
  const nightPick = async (name) => { try { await sendNight(name); } catch { /* ignore */ } };

  return (
    <section className="play-panel">
      <div className="you-banner">
        <span>You are</span> <b>{you.name}</b>
        <span className={`role-tag ${you.role}`}>{ROLE_EMOJI[you.role]} {you.role}</span>
        {dead && <span className="you-dead">💀 eliminated</span>}
      </div>

      {you.goal && <div className="goal">🎯 <b>Your goal:</b> {you.goal}</div>}
      {you.partner && <div className="secret wolf">🐺 Your werewolf partner: <b>{you.partner}</b></div>}
      {you.seer && <div className="secret seer">🔮 You investigated <b>{you.seer.name}</b> — they are a <b>{you.seer.role}</b></div>}

      {/* ---------- NIGHT controls ---------- */}
      {isNight && !dead && awaiting?.kind === "seer" && (
        <div className="your-turn">
          <div className="turn-label">🔮 Investigate whose true role?</div>
          <div className="vote-opts">
            {awaiting.options.map((n) => (
              <button key={n} className="btn toggle vote-btn" onClick={() => nightPick(n)}>{nameOf(n)}</button>
            ))}
          </div>
        </div>
      )}

      {isNight && !dead && awaiting?.kind === "wolf_kill" && (() => {
        const wv = you.wolfVotes || {};
        const killCount = (n) => Object.values(wv).filter((t) => t === n).length;
        return (
          <div className="your-turn">
            <div className="turn-label">🐺 Wolf night — agree on tonight's kill</div>
            {Object.entries(wv).map(([w, t]) => (
              <div key={w} className="wolf-vote-line">
                <b>{nameOf(w)}{w === you.name ? " (you)" : ""}</b> → 🔪 <b>{nameOf(t)}</b>
              </div>
            ))}
            {(you.wolfChat || []).map((c, i) => (
              <div key={i} className="wolf-line"><b>{nameOf(c.speaker)}:</b> {c.text}</div>
            ))}
            <div className="vote-opts">
              {awaiting.options.map((n) => (
                <button key={n} className={`btn toggle vote-btn ${wv[you.name] === n ? "voted" : ""}`} onClick={() => nightPick(n)}>
                  🔪 {nameOf(n)}{killCount(n) > 0 ? ` (${killCount(n)})` : ""}
                </button>
              ))}
            </div>
            <div className="hint">Match your partner to lock the kill — the most-voted villager dies.</div>
          </div>
        );
      })()}

      {isNight && !dead && !awaiting && (
        <div className="watching">🌙 Night falls… you sleep while the village's fate is decided.</div>
      )}

      {/* ---------- DAY controls ---------- */}
      {isDay && !dead && (
        <div className="your-turn">
          <div className="turn-label">
            🗣️ Daytime debate {secsLeft != null && <span className="day-timer">⏳ {secsLeft}s</span>}
          </div>
          {haveFloor ? (
            <>
              <div className="floor-cue">✋ You have the floor — speak now!</div>
              <textarea
                rows={3} autoFocus value={text} disabled={busy}
                placeholder="Say it to the table…"
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit(); }}
              />
              <button className="btn start" disabled={busy || !text.trim()} onClick={submit}>Send {busy ? "…" : "▶"}</button>
            </>
          ) : (
            <button className="btn toggle raise-btn" onClick={ask}>✋ Raise hand to speak</button>
          )}

          <div className="turn-label vote-label">
            🗳️ Your vote — <span className="muted">your pick is secret, the tally is public</span>
          </div>
          <div className="vote-track">
            {(state.players || []).filter((p) => p.alive).map((p) => (
              <span key={p.idx} className={`vtrack ${(state.voters || []).includes(p.name) ? "did" : ""}`}>
                {(state.voters || []).includes(p.name) ? "✓" : "·"} {nameOf(p.name)}
              </span>
            ))}
            <span className="vtrack total">{(state.voters || []).length}/{state.aliveCount} voted</span>
          </div>
          <div className="vote-opts">
            {others.map((p) => {
              const c = (state.voteCounts || {})[p.name] || 0;
              return (
                <button key={p.name} className={`btn toggle vote-btn ${you.vote === p.name ? "voted" : ""}`} onClick={() => vote(p.name)}>
                  {nameOf(p.name)}{c > 0 ? ` (${c})` : ""}
                </button>
              );
            })}
            <button className={`btn toggle skip-btn ${!you.vote ? "skipping" : ""}`} onClick={() => sendVote("")}>
              🚫 Skip
            </button>
          </div>
        </div>
      )}

      {dead && <div className="watching">💀 You're out — watch how it plays out.</div>}
    </section>
  );
}
