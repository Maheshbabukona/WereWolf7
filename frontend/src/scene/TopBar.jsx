export default function TopBar({ state, onExit }) {
  const agents = state?.players?.length ? state.players.length - 1 : null;
  return (
    <header className="topbar">
      <div className="brand">🐺 PACK</div>
      <div className="tagline">{agents != null ? `You + ${agents} AI agents` : "Play yourself"}</div>
      {state?.agentProvider && (
        <div className={`llm-badge ${state.agentProvider === "mock" ? "mock" : "live"}`}>
          {state.agentProvider === "mock" ? "⚠ MOCK AGENTS" : `🤖 ${state.agentProvider}`}
        </div>
      )}
      <div className="spacer" />
      {state?.winner && (
        <div className={`winner-badge ${state.winner}`}>🏆 {state.winner} win</div>
      )}
      <button className="btn exit" onClick={onExit}>🚪 Exit game</button>
    </header>
  );
}
