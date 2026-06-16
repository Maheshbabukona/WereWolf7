"""Runtime configuration — the single place that reads the environment.

Nothing else in the codebase should touch os.environ. Import `config` and read
attributes. `.env` is loaded here if python-dotenv is available.
"""
import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


class Config:
    def __init__(self):
        # --- LLM (OpenAI) ---
        self.openai_api_key: str = os.environ.get("OPENAI_API_KEY", "").strip()
        self.openai_model: str = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        # No key => keyless mock mode (canned agents, no cost).
        self.use_mock: bool = not bool(self.openai_api_key)

        # --- Pacing --- (PACE=0 runs instantly; >1 slows the "beats")
        self.pace: float = float(os.environ.get("PACE", "1.0"))

        # --- Director-orchestrated day --- (time-based, not fixed rounds)
        # How long the daytime debate runs before the hidden ballot is tallied.
        self.day_seconds: float = float(os.environ.get("DAY_SECONDS", "120"))
        # How long the night runs (seer investigates, wolves agree on a kill).
        self.night_seconds: float = float(os.environ.get("NIGHT_SECONDS", "30"))

    @property
    def llm_mode(self) -> str:
        return "MOCK" if self.use_mock else f"OPENAI:{self.openai_model}"


config = Config()
