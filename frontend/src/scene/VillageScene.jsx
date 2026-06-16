import { useEffect, useState } from "react";
import Character from "./Character";

// Fit the ring inside the ACTUAL stage box (measured live with a
// ResizeObserver). The ring is centered in the space ABOVE the dialogue box, so
// the bottom seats never hide under the speaker overlay.
const MARGIN_X = 135;     // half character width + side breathing room
const MARGIN_TOP = 110;   // avatar half above the ring line
const DIALOGUE_BAND = 260; // bottom space reserved for the JRPG speaker box

function useRingLayout() {
  const [el, setEl] = useState(null);
  const [layout, setLayout] = useState({ radius: 160, cy: 200 });
  useEffect(() => {
    if (!el) return;
    const measure = () => {
      const { width: w, height: h } = el.getBoundingClientRect();
      const top = MARGIN_TOP;
      const bottom = Math.max(top + 240, h - DIALOGUE_BAND); // ring stays above the box
      const cy = (top + bottom) / 2;                          // center the ring there
      const byH = (bottom - top) / 2;
      const byW = w / 2 - MARGIN_X;
      const radius = Math.max(120, Math.min(320, Math.round(Math.min(byH, byW))));
      setLayout({ radius, cy: Math.round(cy) });
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [el]);
  return [setEl, layout];
}

function ringStyle(idx, total, radius, cy) {
  const a = (idx / total) * 2 * Math.PI - Math.PI / 2; // start at top, clockwise
  return {
    left: `calc(50% + ${Math.cos(a) * radius}px)`,
    top: `${cy + Math.sin(a) * radius}px`,
    transform: "translate(-50%, -50%)",
  };
}

// Day backdrop for setup/discussion/voting; the pale (night) variant for the
// night + morning beats, so the chosen scene drives the day/night mood.
function sceneBg(state) {
  if (!state?.scene) return undefined;
  const night = state.phase === "night" || state.phase === "setup";
  return `url(/scenes/${state.scene}_${night ? "night" : "day"}.png)`;
}

export default function VillageScene({ state, godMode }) {
  const [sceneRef, { radius, cy }] = useRingLayout();
  if (!state || state.phase === "idle" || !state.players?.length) {
    return (
      <div className="scene empty" ref={sceneRef}>
        <div className="empty-hint">Press ▶ Start to gather the village</div>
      </div>
    );
  }
  const total = state.players.length;
  return (
    <div className="scene" ref={sceneRef} style={{ backgroundImage: sceneBg(state) }}>
      {state.players.map((p) => (
        <Character
          key={p.idx}
          player={p}
          isSpeaking={state.speakingIdx === p.idx}
          godMode={godMode}
          style={ringStyle(p.idx, total, radius, cy)}
        />
      ))}
    </div>
  );
}
