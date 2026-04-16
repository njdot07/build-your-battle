"""
ui/components.py
================
Reusable pygame UI widgets.

  • TextInput        — keyboard-driven single-line input with cursor + focus
  • ParallaxManager  — three scrolling background layers for 2.5D depth
"""

from __future__ import annotations

import math
import random

import pygame


# ---------------------------------------------------------------------------
# TextInput
# ---------------------------------------------------------------------------
class TextInput:
    """A simple, game-menu-styled text input widget.

    Event-driven: call `handle_event(event)` for every pygame event when
    the widget is active.  Printable characters are appended; backspace
    and delete are respected; arrow keys move the caret; Enter fires
    the `on_submit` callback (if provided).
    """

    def __init__(self, rect, font, *,
                 max_chars: int = 48,
                 placeholder: str = "",
                 on_submit=None,
                 colors: dict | None = None):
        self.rect = pygame.Rect(rect)
        self.font = font
        self.max_chars = max_chars
        self.placeholder = placeholder
        self.on_submit = on_submit
        self.text = ""
        self.cursor = 0          # caret index into self.text
        self.focused = True
        self._blink_frame = 0

        # Palette — override any key via the `colors` kwarg
        self.colors = {
            "bg":          (28, 32, 58),
            "bg_focus":    (36, 42, 72),
            "border":      (90, 110, 150),
            "border_focus": (0, 240, 220),
            "text":        (240, 240, 255),
            "placeholder": (140, 150, 180),
            "caret":       (255, 255, 255),
        }
        if colors:
            self.colors.update(colors)

    # -- input -----------------------------------------------------------
    def set_text(self, text: str) -> None:
        self.text = text[:self.max_chars]
        self.cursor = len(self.text)

    def clear(self) -> None:
        self.text = ""
        self.cursor = 0

    def handle_event(self, event) -> bool:
        """Return True if the event was consumed by the input."""
        if not self.focused:
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Clicking on us grabs focus; clicking outside loses it.
            self.focused = self.rect.collidepoint(event.pos)
            return self.focused

        if event.type != pygame.KEYDOWN:
            return False

        if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
            if self.on_submit:
                self.on_submit(self.text)
            return True
        if event.key == pygame.K_BACKSPACE:
            if self.cursor > 0:
                self.text = self.text[:self.cursor - 1] + self.text[self.cursor:]
                self.cursor -= 1
            return True
        if event.key == pygame.K_DELETE:
            self.text = self.text[:self.cursor] + self.text[self.cursor + 1:]
            return True
        if event.key == pygame.K_LEFT:
            self.cursor = max(0, self.cursor - 1)
            return True
        if event.key == pygame.K_RIGHT:
            self.cursor = min(len(self.text), self.cursor + 1)
            return True
        if event.key == pygame.K_HOME:
            self.cursor = 0
            return True
        if event.key == pygame.K_END:
            self.cursor = len(self.text)
            return True

        # Any other printable character — pygame populates event.unicode
        # with the localised glyph.  Filter out control chars.
        ch = event.unicode
        if ch and ch.isprintable() and len(self.text) < self.max_chars:
            self.text = self.text[:self.cursor] + ch + self.text[self.cursor:]
            self.cursor += 1
            return True
        return False

    # -- draw ------------------------------------------------------------
    def draw(self, surface) -> None:
        self._blink_frame += 1

        bg = self.colors["bg_focus"] if self.focused else self.colors["bg"]
        bc = self.colors["border_focus"] if self.focused else self.colors["border"]
        pygame.draw.rect(surface, bg, self.rect, border_radius=6)
        pygame.draw.rect(surface, bc, self.rect, 2, border_radius=6)

        # Text or placeholder
        if self.text:
            text_surf = self.font.render(self.text, True, self.colors["text"])
        else:
            text_surf = self.font.render(
                self.placeholder, True, self.colors["placeholder"])
        text_rect = text_surf.get_rect(
            midleft=(self.rect.x + 12, self.rect.centery))
        # clip text to the input bounds
        clip_area = pygame.Rect(self.rect.x + 8, text_rect.y,
                                self.rect.w - 16, text_rect.h)
        surface.set_clip(clip_area)
        surface.blit(text_surf, text_rect)
        surface.set_clip(None)

        # Caret
        if self.focused and (self._blink_frame // 30) % 2 == 0:
            prefix = self.text[:self.cursor]
            caret_x = text_rect.x + self.font.size(prefix)[0]
            pygame.draw.line(
                surface, self.colors["caret"],
                (caret_x, self.rect.y + 6),
                (caret_x, self.rect.bottom - 6), 2)


# ---------------------------------------------------------------------------
# ParallaxManager
# ---------------------------------------------------------------------------
# Each layer is a pre-rendered pygame.Surface with transparent areas.
# When we draw, we offset the layer by a factor of the camera position —
# distant layers barely move, near layers scroll fast.  Because all
# layers are the same width as the screen, we tile them horizontally:
# draw the same surface twice side-by-side, wrapping with modulo.

class ParallaxManager:
    """Three-layer parallax background with theme-driven palettes.

    Themes correspond to the `theme` field returned by the AI character
    generator ("fire", "ice", "electric", "void", "nature", "arcane").
    Each theme defines a sky colour plus three layer colour triples
    used for the silhouette shapes.

    Update with `set_theme(name)` to swap palettes.  Draw each frame
    with `draw(surface, camera_x)`.
    """

    THEMES = {
        "fire": {
            "sky":  [(60, 18, 12),  (85, 25, 15)],
            "layer0": (35, 15, 20),   # distant peaks
            "layer1": (80, 30, 25),   # mid hills
            "layer2": (130, 45, 30),  # near ridge
            "accent": (255, 140, 50),
        },
        "ice": {
            "sky":  [(20, 40, 70),  (35, 60, 100)],
            "layer0": (30, 50, 80),
            "layer1": (70, 110, 150),
            "layer2": (130, 180, 220),
            "accent": (210, 235, 255),
        },
        "electric": {
            "sky":  [(15, 10, 40),  (30, 15, 60)],
            "layer0": (25, 10, 50),
            "layer1": (60, 30, 110),
            "layer2": (120, 80, 200),
            "accent": (240, 220, 90),
        },
        "void": {
            "sky":  [(8, 6, 20),   (14, 10, 30)],
            "layer0": (10, 8, 25),
            "layer1": (35, 25, 60),
            "layer2": (70, 50, 110),
            "accent": (180, 120, 220),
        },
        "nature": {
            "sky":  [(30, 50, 45),  (55, 85, 70)],
            "layer0": (20, 40, 30),
            "layer1": (45, 75, 50),
            "layer2": (80, 125, 75),
            "accent": (180, 230, 140),
        },
        "arcane": {
            "sky":  [(25, 20, 50),  (45, 30, 80)],
            "layer0": (30, 20, 60),
            "layer1": (70, 40, 110),
            "layer2": (130, 80, 190),
            "accent": (230, 180, 255),
        },
    }

    # Slower numbers = further away.  Near layer should scroll faster
    # than the player so it feels close.
    SCROLL_FACTORS = (0.10, 0.30, 0.55)

    def __init__(self, screen_w: int, screen_h: int, ground_y: int):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.ground_y = ground_y
        self.theme = "arcane"
        self._layers: list[pygame.Surface] = []
        self._sky: pygame.Surface | None = None
        self._build_surfaces()

    # -- theme swap ------------------------------------------------------
    def set_theme(self, theme: str) -> None:
        if theme not in self.THEMES:
            theme = "arcane"
        if theme == self.theme and self._layers:
            return
        self.theme = theme
        self._build_surfaces()

    # -- draw ------------------------------------------------------------
    def draw(self, surface: pygame.Surface, camera_x: float = 0.0) -> None:
        # Sky first (no scrolling — it's the infinite backdrop)
        if self._sky is not None:
            surface.blit(self._sky, (0, 0))

        for layer, factor in zip(self._layers, self.SCROLL_FACTORS):
            offset = -int(camera_x * factor) % self.screen_w
            # Two copies side-by-side for seamless wrap
            surface.blit(layer, (offset - self.screen_w, 0))
            surface.blit(layer, (offset, 0))

    # -- build -----------------------------------------------------------
    def _build_surfaces(self) -> None:
        """Render three silhouette layers into pygame.Surfaces.

        We procedurally draw polygon mountain ranges / spires at
        decreasing distance so we don't need any image assets.
        """
        palette = self.THEMES[self.theme]

        # Sky gradient
        self._sky = pygame.Surface((self.screen_w, self.screen_h))
        top, bot = palette["sky"]
        for y in range(self.screen_h):
            t = y / self.screen_h
            r = int(top[0] * (1 - t) + bot[0] * t)
            g = int(top[1] * (1 - t) + bot[1] * t)
            b = int(top[2] * (1 - t) + bot[2] * t)
            pygame.draw.line(self._sky, (r, g, b),
                             (0, y), (self.screen_w, y))

        # Seed so each theme draws deterministic silhouettes
        rng = random.Random(hash(self.theme) & 0xFFFF)

        layer_configs = [
            # (colour, baseline y, peak height, seg count)
            (palette["layer0"], int(self.ground_y * 0.55),
             int(self.ground_y * 0.15), 10),
            (palette["layer1"], int(self.ground_y * 0.70),
             int(self.ground_y * 0.20), 14),
            (palette["layer2"], int(self.ground_y * 0.85),
             int(self.ground_y * 0.22), 18),
        ]

        self._layers = []
        for colour, baseline, height, segs in layer_configs:
            surf = pygame.Surface((self.screen_w, self.screen_h),
                                  pygame.SRCALPHA)
            points = [(0, self.screen_h)]
            for i in range(segs + 1):
                x = int(self.screen_w * i / segs)
                # Combine sine for smooth ridges with random jitter for texture
                y = baseline - int(
                    math.sin(i * 1.3 + rng.random() * 2) *
                    (height * 0.6 + rng.random() * height * 0.4))
                points.append((x, y))
            points.append((self.screen_w, self.screen_h))
            pygame.draw.polygon(surf, colour, points)

            # A few tiny accent dots (embers / stars / motes) on the layer
            accent = palette["accent"]
            dot_count = {0: 8, 1: 14, 2: 20}[layer_configs.index(
                (colour, baseline, height, segs))]
            for _ in range(dot_count):
                dx = rng.randint(0, self.screen_w)
                dy = rng.randint(0, baseline - 20)
                r = rng.randint(1, 2)
                pygame.draw.circle(surf, accent, (dx, dy), r)

            self._layers.append(surf)
