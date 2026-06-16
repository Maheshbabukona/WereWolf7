"""Lightweight session identity — one player per session id.

No login: the client generates/stores a session id (cookie or localStorage) and
sends it on each request. We keep a tiny in-memory map sid -> {name, avatar,
theme, scene}. (In-memory is fine while rooms live in one process; swap for
Redis/DB when we scale — see docs/PLAN.md §9.)
"""
import secrets

from . import themes

_sessions: dict[str, dict] = {}


def new_sid() -> str:
    return secrets.token_urlsafe(16)


def get(sid: str | None) -> dict | None:
    if not sid:
        return None
    return _sessions.get(sid)


def save(sid: str, name: str, avatar: str, theme: str, scene: str) -> dict:
    theme = theme if theme in themes.THEMES else themes.DEFAULT_THEME
    chars = themes.characters_for(theme)
    data = {
        "name": name.strip()[:24] or "Stranger",
        "avatar": avatar if avatar in chars else chars[0],
        "theme": theme,
        "scene": themes.valid_scene(theme, scene),
    }
    _sessions[sid] = data
    return data
