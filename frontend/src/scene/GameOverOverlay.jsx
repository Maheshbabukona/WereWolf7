const ROLE_EMOJI = { wolf: "🐺", seer: "🔮", villager: "🧑‍🌾" };

export default function GameOverOverlay({ state, onNewGame, onHome }) {
  if (!state || state.phase !== "ended") return null;
  const winner = state.winner;
  // Tell the human how THEY did.
  const you = state.you;
  let youResult = null;
  if (you) {
    const wonTeam = (you.role === "wolf") === (winner === "wolves");
    youResult = { won: wonTeam, alive: you.alive };
  }
  return (
    <div className="overlay">
      <div className="overlay-card">
        <div className={`overlay-winner ${winner}`}>
          {winner === "wolves" ? "🐺 Wolves win" : "🧑‍🌾 Village wins"}
        </div>
        {youResult && (
          <div className={`you-result ${youResult.won ? "win" : "lose"}`}>
            {youResult.won ? "🎉 You win!" : "💀 You lose."}{" "}
            ({you.role}, {youResult.alive ? "survived" : "eliminated"})
          </div>
        )}
        <div className="overlay-roles">
          {state.players.map((p) => (
            <div key={p.idx} className={`reveal-row ${p.role}`}>
              <span>{ROLE_EMOJI[p.role]}</span>
              <span className="rv-name">{p.name}{p.isHuman ? " (you)" : ""}</span>
              <span className="rv-role">{p.role}</span>
              <span className="rv-state">{p.alive ? "survived" : "eliminated"}</span>
            </div>
          ))}
        </div>
        <div className="overlay-actions">
          <button className="btn start big" onClick={onNewGame}>▶ New game</button>
          <button className="btn big" onClick={onHome}>🏠 Home</button>
        </div>
      </div>
    </div>
  );
}
