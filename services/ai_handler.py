"""
services/ai_handler.py
======================
Threaded client for the local LM Studio OpenAI-compatible endpoint.

The game thread never blocks on the network — requests run in a worker
thread and results are delivered through a queue that the game loop
polls once per frame.

Usage pattern:
    ai = AIHandler()
    ai.request_character("a fire-breathing golem")
    # ... each frame:
    result = ai.poll()
    if result is not None:
        # dict with name/health/attack/... or {"error": "..."}
        ...

If LM Studio is not reachable (ConnectionError / timeout), a deterministic
fallback character is returned instead of crashing the game.
"""

from __future__ import annotations

import json
import queue
import random
import re
import threading
import urllib.error
import urllib.request


# The endpoint exposed by LM Studio when the OpenAI compatibility server
# is running.  Override LM_STUDIO_URL env var if you host it elsewhere.
LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
LM_STUDIO_TIMEOUT = 25.0   # seconds


SYSTEM_PROMPT = (
    "You are a fighter generator for a 2D PvE arena brawler.\n"
    "Given a character description, respond with a SINGLE JSON object ONLY "
    "— no prose, no code fences, just the raw JSON. Use this exact schema:\n"
    "{\n"
    '  "name": string (1-14 chars),\n'
    '  "health": int 140-320,\n'
    '  "attack": int 15-40,\n'
    '  "defense": int 2-9,\n'
    '  "speed": int 4-9,\n'
    '  "theme": one of ["fire","ice","electric","void","nature","arcane"],\n'
    '  "color": [int r, int g, int b] (body colour, 0-255 each),\n'
    '  "proj_color": [int r, int g, int b] (projectile colour),\n'
    '  "lore": string (one sentence, under 90 chars)\n'
    "}\n"
    "Stats should feel balanced: tanks have more health + defense but lower "
    "speed and attack.  Glass-cannons are the reverse.  Pick colours that "
    "fit the description and theme.  Do not include any other text."
)


# ---------------------------------------------------------------------------
# Fallbacks and validation
# ---------------------------------------------------------------------------
FALLBACK_THEMES = {
    "fire":     {"color": [220, 90, 50],   "proj_color": [255, 180, 60]},
    "ice":      {"color": [120, 190, 230], "proj_color": [200, 240, 255]},
    "electric": {"color": [180, 120, 255], "proj_color": [255, 240, 120]},
    "void":     {"color": [60, 30, 90],    "proj_color": [180, 100, 220]},
    "nature":   {"color": [80, 180, 80],   "proj_color": [160, 255, 120]},
    "arcane":   {"color": [200, 100, 220], "proj_color": [240, 200, 255]},
}


def _clamp(v, lo, hi):
    try:
        return max(lo, min(hi, int(v)))
    except (TypeError, ValueError):
        return (lo + hi) // 2


def _clamp_color(c, fallback):
    if not isinstance(c, (list, tuple)) or len(c) < 3:
        return tuple(fallback)
    try:
        return tuple(max(0, min(255, int(c[i]))) for i in range(3))
    except (TypeError, ValueError):
        return tuple(fallback)


def _validate(raw: dict, description: str) -> dict:
    """Clamp/normalise AI output so we never hand the game bad data."""
    theme = raw.get("theme", "arcane")
    if theme not in FALLBACK_THEMES:
        theme = "arcane"
    fb = FALLBACK_THEMES[theme]

    name = str(raw.get("name", "Champion"))[:14].strip() or "Champion"

    return {
        "name":       name,
        "health":     _clamp(raw.get("health", 200), 140, 320),
        "attack":     _clamp(raw.get("attack", 20), 15, 40),
        "defense":    _clamp(raw.get("defense", 4), 2, 9),
        "speed":      _clamp(raw.get("speed", 6), 4, 9),
        "theme":      theme,
        "color":      _clamp_color(raw.get("color"), fb["color"]),
        "proj_color": _clamp_color(raw.get("proj_color"), fb["proj_color"]),
        "lore":       str(raw.get("lore", "A mysterious champion."))[:120],
        "source":     "ai",
        "description": description,
    }


def _fallback_character(description: str, reason: str) -> dict:
    """Deterministic-ish fallback so the game still works offline."""
    seed = sum(ord(c) for c in description) or 1
    rng = random.Random(seed)
    theme = rng.choice(list(FALLBACK_THEMES.keys()))
    fb = FALLBACK_THEMES[theme]
    return {
        "name":       description[:14].title() or "Offline Hero",
        "health":     rng.randint(180, 260),
        "attack":     rng.randint(18, 30),
        "defense":    rng.randint(3, 7),
        "speed":      rng.randint(5, 8),
        "theme":      theme,
        "color":      tuple(fb["color"]),
        "proj_color": tuple(fb["proj_color"]),
        "lore":       f"An offline approximation — {description}.",
        "source":     "fallback",
        "description": description,
        "fallback_reason": reason,
    }


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------
def _extract_json(text: str) -> dict | None:
    """Pull the first top-level JSON object from free-form LLM output.

    LLMs sometimes wrap JSON in code fences or add a leading sentence,
    so we scan for the first '{' and match braces until we have a
    balanced object, then try to parse it.
    """
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                chunk = text[start:i + 1]
                try:
                    return json.loads(chunk)
                except json.JSONDecodeError:
                    # try to repair trailing commas
                    repaired = re.sub(r",\s*([}\]])", r"\1", chunk)
                    try:
                        return json.loads(repaired)
                    except json.JSONDecodeError:
                        return None
    return None


# ---------------------------------------------------------------------------
# AIHandler — thin threaded client
# ---------------------------------------------------------------------------
class AIHandler:
    """Non-blocking client for LM Studio's chat-completions endpoint."""

    def __init__(self, url: str = LM_STUDIO_URL,
                 timeout: float = LM_STUDIO_TIMEOUT):
        self.url = url
        self.timeout = timeout
        self._queue: queue.Queue = queue.Queue()
        self._worker: threading.Thread | None = None

    # -- public API --------------------------------------------------------
    def request_character(self, description: str) -> None:
        """Kick off a character-generation request.  Non-blocking.

        If a previous request is still running, this call is ignored —
        callers should check `is_busy()` first.
        """
        if self.is_busy():
            return
        description = (description or "").strip()
        if not description:
            self._queue.put(_fallback_character(
                "anonymous", "empty description"))
            return
        self._worker = threading.Thread(
            target=self._worker_fn, args=(description,), daemon=True)
        self._worker.start()

    def is_busy(self) -> bool:
        return self._worker is not None and self._worker.is_alive()

    def poll(self) -> dict | None:
        """Return the next completed result or None if none is ready."""
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    # -- worker -----------------------------------------------------------
    def _worker_fn(self, description: str) -> None:
        try:
            payload = {
                "model": "local-model",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": f"Description: {description}"},
                ],
                "temperature": 0.8,
                "max_tokens": 300,
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.url, data=data,
                headers={"Content-Type": "application/json"},
                method="POST")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8", errors="replace")
            envelope = json.loads(body)
            content = (envelope.get("choices") or [{}])[0] \
                .get("message", {}).get("content", "")
            parsed = _extract_json(content)
            if parsed is None:
                self._queue.put(_fallback_character(
                    description, "LLM returned non-JSON output"))
                return
            self._queue.put(_validate(parsed, description))
        except (urllib.error.URLError, urllib.error.HTTPError,
                TimeoutError, ConnectionError, OSError) as e:
            self._queue.put(_fallback_character(
                description, f"LM Studio unreachable: {e}"))
        except Exception as e:  # noqa: BLE001 — final safety net
            self._queue.put(_fallback_character(
                description, f"Unexpected error: {e}"))
