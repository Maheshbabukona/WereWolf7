"""Themes — an art family that binds a set of scenes (backdrops) to a roster of
character sprites. The lobby lets a player pick a theme, then a scene + their
character from THAT theme; agents are drawn from the same theme's roster so the
whole table is visually coherent (see docs/PLAN.md).

We currently ship one complete theme (Fantasy: 4 scenes, 23 chibi characters).
Adding another theme = adding matching scene + character art and a dict entry.
Scene images live at  frontend/public/scenes/<scene>_<day|night>.png
Character sprites at   frontend/public/avatars/<slug>.png
"""
from .avatars import AVATARS

THEMES = {
    "fantasy": {
        "label": "Fantasy",
        "scenes": [
            {"id": "scene1", "label": "Ancient Ruins"},
            {"id": "scene2", "label": "Dragon Hall"},
            {"id": "scene3", "label": "Wildwood"},
            {"id": "scene4", "label": "The Crypt"},
        ],
        "characters": AVATARS,
    },
}

DEFAULT_THEME = "fantasy"


def theme(name: str | None) -> dict:
    return THEMES.get(name or DEFAULT_THEME, THEMES[DEFAULT_THEME])


def valid_scene(theme_name: str | None, scene_id: str | None) -> str:
    t = theme(theme_name)
    ids = [s["id"] for s in t["scenes"]]
    return scene_id if scene_id in ids else ids[0]


def characters_for(theme_name: str | None) -> list[str]:
    return list(theme(theme_name)["characters"])
