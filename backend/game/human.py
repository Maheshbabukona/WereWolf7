"""Human input for the director-orchestrated day.

The human lives UNDER the Director: they don't speak on a fixed turn, they
RAISE A HAND. The day loop sees the raised hand, finishes the current beat, then
hands them the floor (blocking on an Event until they submit their line). They
also set a hidden vote at any time. Single game at a time, so module state
suffices.
"""
import threading

_event = threading.Event()
_value = None
_lock = threading.Lock()
_hand = False
_vote: str | None = None


# ---- raise hand -> take the floor ----------------------------------------- #
def raise_hand() -> None:
    global _hand
    with _lock:
        _hand = True


def take_hand() -> bool:
    """Read-and-clear: did the human ask for the floor?"""
    global _hand
    with _lock:
        v = _hand
        _hand = False
        return v


def peek_hand() -> bool:
    """Read without clearing — lets a readable pause end early if a hand is up."""
    with _lock:
        return _hand


def begin() -> None:
    """Reset before the loop waits for the human's floor line."""
    global _value
    with _lock:
        _value = None
        _event.clear()


def submit(value) -> None:
    """The human's floor line (POST /control/say)."""
    global _value
    with _lock:
        _value = value
    _event.set()


def wait(timeout: float):
    """Block until submit() or timeout. Returns the line, or None on timeout."""
    got = _event.wait(timeout)
    with _lock:
        return _value if got else None


# ---- hidden vote (any time) ----------------------------------------------- #
def set_vote(target: str | None) -> None:
    global _vote
    with _lock:
        _vote = target


def get_vote() -> str | None:
    with _lock:
        return _vote


# ---- night action (seer investigate / wolf kill pick) --------------------- #
_night_action: str | None = None


def set_night_action(target: str | None) -> None:
    global _night_action
    with _lock:
        _night_action = target


def get_night_action() -> str | None:
    with _lock:
        return _night_action


def reset() -> None:
    global _hand, _vote, _value, _night_action
    with _lock:
        _hand = False
        _vote = None
        _value = None
        _night_action = None
        _event.clear()
