# pyrefly: ignore [missing-import]
import pygame
import math
from settings import (
    WINDOW_W, WINDOW_H, C_BG, TILE_SIZE, C_HUD_ACCENT,
    C_HUD_TEXT, C_HUD_BG, DEFAULT_VOLUME
)

# ─────────────────────────── shared helpers ───────────────────────────

def _render_centered(surface, text, font, color, y):
    surf = font.render(text, True, color)
    surface.blit(surf, (WINDOW_W // 2 - surf.get_width() // 2, y))


def _make_fonts():
    title  = pygame.font.SysFont('Courier New', 42, bold=True)
    heading = pygame.font.SysFont('Courier New', 24, bold=True)
    body    = pygame.font.SysFont('Courier New', 18, bold=False)
    small   = pygame.font.SysFont('Courier New', 14, bold=False)
    return title, heading, body, small


def _draw_bg(surface, tick):
    """Animated grid background."""
    surface.fill(C_BG)
    offset = int(tick * 0.3) % 48
    for x in range(-TILE_SIZE, WINDOW_W + TILE_SIZE, TILE_SIZE):
        pygame.draw.line(surface, (28, 38, 52), (x + offset, 0), (x + offset, WINDOW_H), 1)
    for y in range(-TILE_SIZE, WINDOW_H + TILE_SIZE, TILE_SIZE):
        pygame.draw.line(surface, (28, 38, 52), (0, y + offset), (WINDOW_W, y + offset), 1)


def _draw_title(surface, font_title, tick):
    text  = "BomberPy"
    glow  = abs(math.sin(math.radians(tick * 0.05))) * 40
    color = (255, int(140 + glow), 20)
    shadow = font_title.render(text, True, (40, 20, 0))
    main   = font_title.render(text, True, color)
    cx = WINDOW_W // 2 - main.get_width() // 2
    surface.blit(shadow, (cx + 3, 63))
    surface.blit(main,   (cx,     60))
    subtitle = pygame.font.SysFont('Courier New', 14).render(
        "SNES EDITION", True, C_HUD_ACCENT)
    surface.blit(subtitle, (WINDOW_W // 2 - subtitle.get_width() // 2, 114))


# ─────────────────────────── MainMenu ─────────────────────────────────

class MainMenu:
    OPTIONS = ["Iniciar Jogo", "Opções", "Sair"]

    def __init__(self):
        self._tick    = 0
        self._cursor  = 0
        self._fonts   = None

    def _ensure_fonts(self):
        if self._fonts is None:
            self._fonts = _make_fonts()

    def handle_event(self, event) -> str | None:
        """Returns action string or None."""
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self._cursor = (self._cursor - 1) % len(self.OPTIONS)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._cursor = (self._cursor + 1) % len(self.OPTIONS)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return self.OPTIONS[self._cursor]
        return None

    def update(self, dt: int):
        self._tick += dt

    def draw(self, surface: pygame.Surface):
        self._ensure_fonts()
        ft, fh, fb, fs = self._fonts
        _draw_bg(surface, self._tick)
        _draw_title(surface, ft, self._tick)

        start_y = 180
        for i, opt in enumerate(self.OPTIONS):
            selected = (i == self._cursor)
            color  = C_HUD_ACCENT if selected else C_HUD_TEXT
            prefix = "► " if selected else "  "
            surf   = fh.render(prefix + opt, True, color)
            cx     = WINDOW_W // 2 - surf.get_width() // 2
            if selected:
                # Highlight box
                pygame.draw.rect(surface, (30, 42, 60),
                                 (cx - 12, start_y + i * 48 - 4,
                                  surf.get_width() + 24, 38), border_radius=6)
                pygame.draw.rect(surface, C_HUD_ACCENT,
                                 (cx - 12, start_y + i * 48 - 4,
                                  surf.get_width() + 24, 38), 2, border_radius=6)
            surface.blit(surf, (cx, start_y + i * 48))

        hint = fs.render("[↑↓] Navegar   [ENTER/ESPAÇO] Confirmar", True, (100, 120, 140))
        surface.blit(hint, (WINDOW_W // 2 - hint.get_width() // 2, WINDOW_H - 30))


# ─────────────────────────── ModeSelect ───────────────────────────────

class ModeSelect:
    OPTIONS = ["PvP Mata-Mata", "Cooperativo (2J vs 2 Bots)", "Voltar"]

    def __init__(self):
        self._tick   = 0
        self._cursor = 0
        self._fonts  = None

    def _ensure_fonts(self):
        if self._fonts is None:
            self._fonts = _make_fonts()

    def handle_event(self, event) -> str | None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self._cursor = (self._cursor - 1) % len(self.OPTIONS)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._cursor = (self._cursor + 1) % len(self.OPTIONS)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return self.OPTIONS[self._cursor]
        return None

    def update(self, dt: int):
        self._tick += dt

    def draw(self, surface: pygame.Surface):
        self._ensure_fonts()
        ft, fh, fb, fs = self._fonts
        _draw_bg(surface, self._tick)
        _draw_title(surface, ft, self._tick)

        _render_centered(surface, "SELECIONE O MODO DE JOGO", fh, C_HUD_TEXT, 150)

        for i, opt in enumerate(self.OPTIONS):
            selected = (i == self._cursor)
            color  = C_HUD_ACCENT if selected else C_HUD_TEXT
            prefix = "► " if selected else "  "
            surf   = fh.render(prefix + opt, True, color)
            cx     = WINDOW_W // 2 - surf.get_width() // 2
            if selected:
                pygame.draw.rect(surface, (30, 42, 60),
                                 (cx - 12, 210 + i * 60 - 4,
                                  surf.get_width() + 24, 38), border_radius=6)
                pygame.draw.rect(surface, C_HUD_ACCENT,
                                 (cx - 12, 210 + i * 60 - 4,
                                  surf.get_width() + 24, 38), 2, border_radius=6)
            surface.blit(surf, (cx, 210 + i * 60))


# ─────────────────────────── PlayerSelect ─────────────────────────────

class PlayerSelect:
    """Choose number of human players (1 or 2) and skins."""

    SKINS = [
        (240, 180,  60),  # Amber
        ( 60, 180, 240),  # Sky Blue
        ( 60, 220, 120),  # Mint
        (220,  80,  60),  # Coral
    ]
    SKIN_NAMES = ["Amber", "Sky Blue", "Mint", "Coral"]

    def __init__(self, num_players: int = 1):
        self._tick       = 0
        self._num        = num_players   # 1 or 2
        self._skins      = [0, 1]        # skin index per player
        self._active_p   = 0            # which player's skin we're editing
        self._confirmed  = False
        self._fonts      = None

    def _ensure_fonts(self):
        if self._fonts is None:
            self._fonts = _make_fonts()

    def handle_event(self, event) -> dict | None:
        """Returns config dict when confirmed, else None."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                self._skins[self._active_p] = (self._skins[self._active_p] - 1) % 4
            elif event.key == pygame.K_RIGHT:
                self._skins[self._active_p] = (self._skins[self._active_p] + 1) % 4
            elif event.key == pygame.K_TAB and self._num > 1:
                self._active_p = 1 - self._active_p
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return {
                    'num_players': self._num,
                    'colors': [self.SKINS[self._skins[i]] for i in range(self._num)],
                }
            elif event.key == pygame.K_ESCAPE:
                return {'back': True}
        return None

    def update(self, dt: int):
        self._tick += dt

    def draw(self, surface: pygame.Surface):
        self._ensure_fonts()
        ft, fh, fb, fs = self._fonts
        _draw_bg(surface, self._tick)
        _draw_title(surface, ft, self._tick)

        _render_centered(surface, "SELECIONE AS SKINS", fh, C_HUD_TEXT, 150)
        hint_tab = "  [TAB] Alternar jogador" if self._num > 1 else ""
        _render_centered(surface, f"[←→] Mudar skin{hint_tab}   [ENTER] Confirmar",
                         fs, (100, 120, 140), 185)

        for pi in range(self._num):
            ox = WINDOW_W // 4 * (pi * 2 + 1)
            skin_color = self.SKINS[self._skins[pi]]
            selected   = (pi == self._active_p)

            # Preview circle
            radius = 36 if selected else 28
            border = C_HUD_ACCENT if selected else C_HUD_TEXT
            pygame.draw.circle(surface, skin_color, (ox, 290), radius)
            pygame.draw.circle(surface, border,     (ox, 290), radius, 3)

            label = fh.render(f"P{pi+1}", True, border)
            surface.blit(label, (ox - label.get_width() // 2, 340))
            sname = fb.render(self.SKIN_NAMES[self._skins[pi]], True, skin_color)
            surface.blit(sname, (ox - sname.get_width() // 2, 368))


# ─────────────────────────── OptionsMenu ──────────────────────────────

class OptionsMenu:
    DIFFICULTIES = ['easy', 'medium', 'hard']
    DIFF_LABELS  = ['Fácil', 'Médio', 'Difícil']
    ITEMS        = ["Volume", "Dificuldade", "Voltar"]

    def __init__(self, volume: float = DEFAULT_VOLUME,
                 difficulty: str = 'medium'):
        self._tick       = 0
        self._cursor     = 0
        self._volume     = volume
        self._diff_idx   = self.DIFFICULTIES.index(difficulty)
        self._fonts      = None

    @property
    def volume(self) -> float:
        return self._volume

    @property
    def difficulty(self) -> str:
        return self.DIFFICULTIES[self._diff_idx]

    def _ensure_fonts(self):
        if self._fonts is None:
            self._fonts = _make_fonts()

    def handle_event(self, event) -> str | None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self._cursor = (self._cursor - 1) % len(self.ITEMS)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._cursor = (self._cursor + 1) % len(self.ITEMS)
            elif event.key == pygame.K_LEFT:
                if self._cursor == 0:
                    self._volume = max(0.0, self._volume - 0.1)
                    pygame.mixer.music.set_volume(self._volume)
                elif self._cursor == 1:
                    self._diff_idx = (self._diff_idx - 1) % 3
            elif event.key == pygame.K_RIGHT:
                if self._cursor == 0:
                    self._volume = min(1.0, self._volume + 0.1)
                    pygame.mixer.music.set_volume(self._volume)
                elif self._cursor == 1:
                    self._diff_idx = (self._diff_idx + 1) % 3
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                if self._cursor == 2 or event.key == pygame.K_ESCAPE:
                    return 'back'
        return None

    def update(self, dt: int):
        self._tick += dt

    def draw(self, surface: pygame.Surface):
        self._ensure_fonts()
        ft, fh, fb, fs = self._fonts
        _draw_bg(surface, self._tick)
        _render_centered(surface, "OPÇÕES", ft, C_HUD_ACCENT, 60)

        items_y = [200, 280, 380]
        values  = [f"{int(self._volume * 100)}%",
                   self.DIFF_LABELS[self._diff_idx],
                   ""]

        for i, (item, val) in enumerate(zip(self.ITEMS, values)):
            selected = (i == self._cursor)
            color    = C_HUD_ACCENT if selected else C_HUD_TEXT
            prefix   = "► " if selected else "  "
            line     = f"{prefix}{item}{'   ' + val if val else ''}"
            surf     = fh.render(line, True, color)
            cx       = WINDOW_W // 2 - surf.get_width() // 2
            surface.blit(surf, (cx, items_y[i]))

            if selected and i == 0:
                # Volume bar
                bar_x = WINDOW_W // 2 - 100
                bar_y = items_y[i] + 34
                pygame.draw.rect(surface, (40, 52, 68), (bar_x, bar_y, 200, 12), border_radius=6)
                filled = int(200 * self._volume)
                pygame.draw.rect(surface, C_HUD_ACCENT, (bar_x, bar_y, filled, 12), border_radius=6)

        hint = fs.render("[↑↓] Navegar   [←→] Ajustar   [ESC] Voltar", True, (100, 120, 140))
        surface.blit(hint, (WINDOW_W // 2 - hint.get_width() // 2, WINDOW_H - 30))


# ─────────────────────────── PauseMenu ────────────────────────────────

class PauseMenu:
    OPTIONS = ["Continuar", "Opções", "Sair para o Menu"]

    def __init__(self):
        self._cursor = 0
        self._fonts  = None

    def _ensure_fonts(self):
        if self._fonts is None:
            self._fonts = _make_fonts()

    def handle_event(self, event) -> str | None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self._cursor = (self._cursor - 1) % len(self.OPTIONS)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._cursor = (self._cursor + 1) % len(self.OPTIONS)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                if event.key == pygame.K_ESCAPE:
                    return "Continuar"
                return self.OPTIONS[self._cursor]
        return None

    def draw(self, surface: pygame.Surface):
        self._ensure_fonts()
        ft, fh, fb, fs = self._fonts

        # Dimmed overlay
        overlay = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))

        # Panel
        panel_w, panel_h = 340, 260
        px = WINDOW_W // 2 - panel_w // 2
        py = WINDOW_H // 2 - panel_h // 2
        pygame.draw.rect(surface, C_HUD_BG, (px, py, panel_w, panel_h), border_radius=12)
        pygame.draw.rect(surface, C_HUD_ACCENT, (px, py, panel_w, panel_h), 2, border_radius=12)

        _render_centered(surface, "PAUSADO", fh, C_HUD_ACCENT, py + 20)

        for i, opt in enumerate(self.OPTIONS):
            selected = (i == self._cursor)
            color    = C_HUD_ACCENT if selected else C_HUD_TEXT
            prefix   = "► " if selected else "  "
            surf     = fh.render(prefix + opt, True, color)
            cx       = WINDOW_W // 2 - surf.get_width() // 2
            surface.blit(surf, (cx, py + 70 + i * 52))


# ─────────────────────────── ResultScreen ─────────────────────────────

class ResultScreen:
    def __init__(self, winner_label: str, scores: list[tuple]):
        self._winner = winner_label
        self._scores = scores    # [(label, score), ...]
        self._tick   = 0
        self._fonts  = None

    def _ensure_fonts(self):
        if self._fonts is None:
            self._fonts = _make_fonts()

    def handle_event(self, event) -> str | None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                return 'menu'
        return None

    def update(self, dt: int):
        self._tick += dt

    def draw(self, surface: pygame.Surface):
        self._ensure_fonts()
        ft, fh, fb, fs = self._fonts
        _draw_bg(surface, self._tick)

        glow  = abs(math.sin(math.radians(self._tick * 0.08))) * 40
        color = (255, int(140 + glow), 20)
        _render_centered(surface, "FIM DE PARTIDA", ft, color, 80)
        _render_centered(surface, f"Vencedor: {self._winner}", fh, C_HUD_TEXT, 160)

        for i, (label, score) in enumerate(self._scores):
            _render_centered(surface, f"{label}: {score:05d} pts",
                             fb, C_HUD_TEXT, 230 + i * 36)

        _render_centered(surface, "[ENTER] Voltar ao Menu", fs, (100, 120, 140),
                         WINDOW_H - 50)
