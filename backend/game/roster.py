"""new_game() to start a fresh match. Cast pool lives in characters.py,
avatar sprites in avatars.py."""
import random

from . import themes
from .characters import NAMES
from .state import GameState, Player

MIN_PLAYERS = 5
MAX_PLAYERS = 12


def _roles_for(total: int) -> list[str]:
    """Role spread for a table of `total`: ~1 wolf per 4 players, 1 seer, rest
    villagers. 5-7 -> 1 wolf, 8-11 -> 2, 12 -> 3."""
    wolves = max(1, total // 4)
    return ["wolf"] * wolves + ["seer"] + ["villager"] * (total - wolves - 1)


def new_game(game_id: int = 1, total_players: int = 7, human: dict | None = None) -> GameState:
    """A fresh match of `total_players` (clamped 5-12).

    One seat is the human (using their chosen name + avatar); the rest are agents
    drawn from the persona pool, each given a distinct sprite avatar. Roles are
    assigned randomly.
    """
    total = max(MIN_PLAYERS, min(MAX_PLAYERS, total_players))
    roles = _roles_for(total)
    random.shuffle(roles)

    human = human or {}
    theme = human.get("theme") or themes.DEFAULT_THEME
    scene = themes.valid_scene(theme, human.get("scene"))
    human_seat = random.randrange(total)
    human_avatar = human.get("avatar")
    # Agents get distinct sprites from the SAME theme so the table is coherent.
    agent_avatars = [a for a in themes.characters_for(theme) if a != human_avatar]
    random.shuffle(agent_avatars)
    agent_names = random.sample(NAMES, total - 1)

    players: list[Player] = []
    ai = 0
    for i in range(total):
        if i == human_seat:
            players.append(Player(
                idx=i,
                name=human.get("name") or "You",
                role=roles[i],
                avatar=human_avatar or agent_avatars[ai],
                is_human=True,
            ))
        else:
            players.append(Player(
                idx=i,
                name=agent_names[ai],
                role=roles[i],
                avatar=agent_avatars[ai],
            ))
            ai += 1
    return GameState(game_id=game_id, theme=theme, scene=scene, players=players)
