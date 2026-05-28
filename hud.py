# pyrefly: ignore [missing-import]
import pygame
from settings import (
    SCREEN_H, WINDOW_W, HUD_H, C_HUD_BG, C_HUD_LINE, C_HUD_TEXT,
    C_POWERUP_R, C_POWERUP_S, C_BOMB, C_BOMB_GLOW
)


class HUD:
    """Renders the bottom HUD strip showing stats for each active player."""

    def __init__(self, players: list):
        self.players = players
        self._font_lg = None
        self._font_sm = None

    def _ensure_fonts(self):
        if self._font_lg is None:
            self._font_lg = pygame.font.SysFont('Courier New', 18, bold=True)
            self._font_sm = pygame.font.SysFont('Courier New', 13, bold=False)

    def draw(self, surface: pygame.Surface):
        self._ensure_fonts()
        hud_y = SCREEN_H
        # Background bar
        pygame.draw.rect(surface, C_HUD_BG, (0, hud_y, WINDOW_W, HUD_H))
        pygame.draw.line(surface, C_HUD_LINE, (0, hud_y), (WINDOW_W, hud_y), 2)

        slot_w = WINDOW_W // max(len(self.players), 1)

        for i, p in enumerate(self.players):
            x_off = i * slot_w
            self._draw_player_slot(surface, p, x_off, hud_y, slot_w)

    def _draw_player_slot(self, surface: pygame.Surface, p,
                          x: int, y: int, w: int):
        pad = 10
        cx  = x + w // 2

        # Label
        label = f"P{p.player_id + 1}" if not hasattr(p, '_interval') else f"BOT{p.player_id - 1}"
        lbl_surf = self._font_lg.render(label, True, p.color)
        surface.blit(lbl_surf, (x + pad, y + 6))

        # Vertical divider
        if x > 0:
            pygame.draw.line(surface, C_HUD_LINE, (x, y), (x, y + HUD_H), 1)

        # Lives (hearts)
        heart_x = x + pad
        heart_y = y + 28
        for i in range(p.lives):
            self._draw_heart(surface, heart_x + i * 18, heart_y, p.color)

        # Score
        score_txt = self._font_sm.render(f"SCORE {p.score:05d}", True, C_HUD_TEXT)
        surface.blit(score_txt, (x + pad, y + 50))

        # Bombs remaining
        bomb_x = cx - 20
        bomb_y = y + 8
        for i in range(p.max_bombs - p.bombs_placed):
            self._draw_bomb_icon(surface, bomb_x + i * 16, bomb_y)

        # Blast range
        range_x = cx + 30
        range_y = y + 8
        range_txt = self._font_sm.render(f"RNG {p.blast_range}", True, C_POWERUP_R)
        surface.blit(range_txt, (range_x, range_y))

        # Speed
        spd_txt = self._font_sm.render(f"SPD {p.speed:.1f}", True, C_POWERUP_S)
        surface.blit(spd_txt, (range_x, range_y + 18))

    # ------------------------------------------------------------------
    # Icon helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _draw_heart(surface, x, y, color):
        pts = [
            (x + 8, y + 14),
            (x,     y + 6),
            (x,     y + 3),
            (x + 4, y),
            (x + 8, y + 4),
            (x + 12, y),
            (x + 16, y + 3),
            (x + 16, y + 6),
        ]
        pygame.draw.polygon(surface, color, pts)

    @staticmethod
    def _draw_bomb_icon(surface, x, y):
        pygame.draw.circle(surface, C_BOMB, (x + 6, y + 9), 5)
        pygame.draw.line(surface, C_BOMB_GLOW, (x + 7, y + 4), (x + 11, y + 1), 2)
        pygame.draw.circle(surface, C_BOMB_GLOW, (x + 12, y), 2)
