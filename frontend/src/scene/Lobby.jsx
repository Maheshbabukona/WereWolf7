import { useEffect, useMemo, useState } from "react";
import { getSession, saveSession } from "../api";

// Pre-game config (Among-Us style): pick a THEME, a SCENE within it, your
// CHARACTER (bound to the theme), size the table, and enter. No login.
// Humans = 1 for now; multi-human online rooms arrive next (docs/PLAN.md).
export default function Lobby({ onEnter }) {
  const [themes, setThemes] = useState({});
  const [meta, setMeta] = useState({});
  const [themeId, setThemeId] = useState("fantasy");
  const [scene, setScene] = useState("scene1");
  const [name, setName] = useState("");
  const [avatar, setAvatar] = useState(null);
  const [total, setTotal] = useState(8);
  const [limits, setLimits] = useState({ min: 5, max: 12 });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const s = await getSession();
        setThemes(s.themes || {});
        setLimits(s.limits || { min: 5, max: 12 });
        setThemeId(s.theme || "fantasy");
        setScene(s.scene || "scene1");
        if (s.name) setName(s.name);
        const chars = (s.themes?.[s.theme || "fantasy"]?.characters) || [];
        setAvatar(s.avatar || chars[Math.floor(Math.random() * chars.length)] || null);
        const m = await fetch("/avatars/manifest.json").then((r) => r.json()).catch(() => []);
        const map = {};
        m.forEach((x) => { map[x.slug] = x; });
        setMeta(map);
      } catch (e) {
        setErr(`Can't reach backend (${e.message}). Is uvicorn running on :8000?`);
      }
    })();
  }, []);

  const theme = themes[themeId];
  const scenes = theme?.scenes || [];
  const chars = useMemo(() => theme?.characters || [], [theme]);

  const pickTheme = (id) => {
    setThemeId(id);
    const t = themes[id];
    setScene(t?.scenes?.[0]?.id || "scene1");
    if (t && !t.characters.includes(avatar)) setAvatar(t.characters[0]);
  };
  const randomize = () => setAvatar(chars[Math.floor(Math.random() * chars.length)]);
  const canStart = name.trim().length > 0 && avatar && !busy;

  const enter = async () => {
    if (!canStart) return;
    setBusy(true); setErr(null);
    try {
      await saveSession(name.trim(), avatar, themeId, scene);
      const res = await onEnter(total);
      if (res && res.ok === false) { setErr(res.reason || "Couldn't start"); setBusy(false); }
    } catch (e) {
      setErr(e.message); setBusy(false);
    }
  };

  return (
    <div className="lobby">
      <div className="lobby-card">
        <h1 className="home-title">🐺 PACK</h1>
        <p className="home-sub">A live social-deduction mind game · you + AI villagers</p>

        {err && <div className="err-banner">⚠ {err}</div>}

        <label className="lobby-label">Your name</label>
        <input
          className="lobby-name"
          value={name}
          maxLength={24}
          placeholder="Enter a name…"
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && enter()}
        />

        {Object.keys(themes).length > 1 && (
          <>
            <div className="lobby-label-row"><span className="lobby-label">Theme</span></div>
            <div className="theme-chips">
              {Object.entries(themes).map(([id, t]) => (
                <button key={id} className={`chip ${themeId === id ? "sel" : ""}`} onClick={() => pickTheme(id)}>
                  {t.label}
                </button>
              ))}
            </div>
          </>
        )}

        <div className="lobby-label-row"><span className="lobby-label">Scene</span></div>
        <div className="scene-row">
          {scenes.map((sc) => (
            <button
              key={sc.id}
              className={`scene-card ${scene === sc.id ? "sel" : ""}`}
              onClick={() => setScene(sc.id)}
            >
              <img src={`/scenes/${sc.id}_day.png`} alt={sc.label} />
              <span>{sc.label}</span>
            </button>
          ))}
        </div>

        <div className="lobby-label-row">
          <span className="lobby-label">Choose your character</span>
          <button className="btn tiny" onClick={randomize}>🎲 Random</button>
        </div>
        <div className="avatar-grid">
          {chars.map((slug) => (
            <button
              key={slug}
              className={`avatar-cell ${avatar === slug ? "sel" : ""}`}
              title={meta[slug]?.label || slug}
              onClick={() => setAvatar(slug)}
            >
              <img src={`/avatars/${slug}.png`} alt={slug} />
            </button>
          ))}
        </div>

        <div className="lobby-label-row">
          <span className="lobby-label">Table size</span>
          <span className="lobby-val">{total} players</span>
        </div>
        <input
          type="range"
          className="lobby-slider"
          min={limits.min}
          max={limits.max}
          value={total}
          onChange={(e) => setTotal(Number(e.target.value))}
        />
        <div className="lobby-breakdown">
          🧑 1 human (you) &nbsp;·&nbsp; 🤖 {total - 1} AI agents
          <span className="lobby-hint"> — more humans unlock with online rooms (next update)</span>
        </div>

        <button className="btn start big lobby-go" disabled={!canStart} onClick={enter}>
          {busy ? "Gathering the village…" : "▶ Enter the village"}
        </button>
      </div>
    </div>
  );
}
