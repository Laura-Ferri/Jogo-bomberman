import pygame
import math
import random
from settings import (
    TILE_SIZE, C_POWERUP_R, C_POWERUP_S, C_POWERUP_B,
    C_WHITE, C_BLACK, C_BOMB_GLOW
)

RANGE_UP   = 'range'
SPEED_UP   = 'speed'
EXTRA_BOMB = 'extra_bomb'
ALL_TYPES  = [RANGE_UP, SPEED_UP, EXTRA_BOMB]


class PowerUp:
    def __init__(self, col: int, row: int):
        self.col   = col
        self.row   = row
        self.x     = col * TILE_SIZE
        self.y     = row * TILE_SIZE
        self.type  = random.choice(ALL_TYPES)
        self.alive = True
        self._t    = 0

    # Slightly-inset rect for pickup detection
    def get_rect(self) -> pygame.Rect:
        m = 8
        return pygame.Rect(self.x + m, self.y + m,
                           TILE_SIZE - m * 2, TILE_SIZE - m * 2)

    def draw(self, surface: pygame.Surface):
        self._t += 4
        pulse = int(math.sin(math.radians(self._t)) * 3)
        r  = 13 + pulse

        # Background glow circle
        glow_surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)

        if self.type == RANGE_UP:
            color = C_POWERUP_R
            # Cross / explosion icon
            pygame.draw.rect(glow_surf, color,
                             (TILE_SIZE//2 - r, TILE_SIZE//2 - 5, r * 2, 10))
            pygame.draw.rect(glow_surf, color,
                             (TILE_SIZE//2 - 5, TILE_SIZE//2 - r, 10, r * 2))
            pygame.draw.rect(glow_surf, C_WHITE,
                             (TILE_SIZE//2 - 3, TILE_SIZE//2 - 3, 6, 6))

        elif self.type == SPEED_UP:
            color = C_POWERUP_S
            # Lightning bolt
            hx, hy = TILE_SIZE // 2, TILE_SIZE // 2
            pts = [
                (hx - 4, hy - r),
                (hx + 6, hy - 2),
                (hx + 1, hy - 2),
                (hx + 6, hy + r),
                (hx - 5, hy + 2),
                (hx - 1, hy + 2),
            ]
            pygame.draw.polygon(glow_surf, color, pts)

        elif self.type == EXTRA_BOMB:
            color = C_POWERUP_B
            # Bomb icon
            bx, by = TILE_SIZE // 2, TILE_SIZE // 2 + 2
            pygame.draw.circle(glow_surf, color, (bx, by), r - 2)
            pygame.draw.circle(glow_surf, C_BLACK, (bx, by), r - 4, 2)
            # Fuse
            pygame.draw.line(glow_surf, C_BOMB_GLOW,
                             (bx + 2, by - r + 6), (bx + 6, by - r + 1), 2)
            pygame.draw.circle(glow_surf, C_BOMB_GLOW,
                               (bx + 7, by - r), 2)

        surface.blit(glow_surf, (self.x, self.y))
