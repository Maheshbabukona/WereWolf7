import { useState } from "react";

// Curated CraftPix chibi sprite per player (player.avatar slug). Falls back to a
// procedural DiceBear pixel-art avatar, then a human emoji, if the image fails.
const COLORS = ["#ef4444", "#3b82f6", "#22c55e", "#f472b6", "#f59e0b", "#a855f7", "#06b6d4"];
const FACES = ["🧑‍🦰", "🧑‍🦱", "🧔", "🧑‍🦳", "👱", "🧑‍🎤", "🧓"];
const ROLE_EMOJI = { wolf: "🐺", seer: "🔮", villager: "🧑‍🌾" };

export default function Character({ player, isSpeaking, godMode, style }) {
  const [stage, setStage] = useState(0); // 0=sprite, 1=dicebear, 2=emoji
  const dead = !player.alive;
  const color = COLORS[player.idx % COLORS.length];
  const seed = encodeURIComponent(player.avatarSeed || player.name);
  const sprite = player.avatar ? `/avatars/${player.avatar}.png` : null;
  const avatar = stage === 0 && sprite
    ? sprite
    : `https://api.dicebear.com/9.x/pixel-art/svg?seed=${seed}`;
  const role = godMode ? player.role : null;
  const shownRole = player.revealedRole || role;

  return (
    <div className={`character ${dead ? "dead" : ""} ${isSpeaking ? "speaking" : ""}`} style={style}>
      <div className="pavatar" style={{ "--c": color }}>
        {stage < 2 ? (
          <img className="pavatar-img" src={avatar} alt={player.name} onError={() => setStage((s) => s + 1)} />
        ) : (
          <span className="pavatar-emoji">{FACES[player.idx % FACES.length]}</span>
        )}
        {dead && <span className="tombstone">🪦</span>}
      </div>

      {/* first name on the ring chip; the full name shows in the dialogue box / feed */}
      <div className="nameplate">{player.name.split(" ")[0]}</div>
      {shownRole && (
        <div className={`role-tag ${shownRole} ${player.revealedRole ? "revealed" : ""}`}>
          {ROLE_EMOJI[shownRole] || ""} {shownRole}
        </div>
      )}
    </div>
  );
}
