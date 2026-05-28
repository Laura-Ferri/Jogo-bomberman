# pyrefly: ignore [missing-import]
import pygame
from settings import (
    TILE_SIZE, EXPLOSION_MS, C_EXPLOSION_O, C_EXPLOSION_M, C_EXPLOSION_C,
    BOMB_FUSE_MS, WALL_SOLID, WALL_SOFT, C_BOMB, C_BOMB_GLOW
)


class Explosion:
    """Single explosion tile — animated flame, auto-expires."""

    def __init__(self, col: int, row: int, kind: str = 'mid'):
        # kind: 'center' | 'mid' | 'tip_up' | 'tip_down' | 'tip_left' | 'tip_right'
        self.col   = col
        self.row   = row
        self.kind  = kind
        self.x     = col * TILE_SIZE
        self.y     = row * TILE_SIZE
        self.alive = True
        self._timer = EXPLOSION_MS
        self._t     = 0

    def update(self, dt: int):
        self._timer -= dt
        self._t += 6
        if self._timer <= 0:
            self.alive = False

    def draw(self, surface: pygame.Surface):
        import math
        progress = 1 - self._timer / EXPLOSION_MS   # 0 → 1
        alpha    = 255 if progress < 0.7 else int(255 * (1 - (progress - 0.7) / 0.3))
        pulse    = abs(math.sin(math.radians(self._t)))

        surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        cx, cy = TILE_SIZE // 2, TILE_SIZE // 2

        # Outer orange
        r_outer = int(18 + pulse * 6)
        pygame.draw.rect(surf, (*C_EXPLOSION_O, alpha),
                         (cx - r_outer, cy - r_outer,
                          r_outer * 2, r_outer * 2))
        # Mid ring
        r_mid = int(12 + pulse * 4)
        pygame.draw.rect(surf, (*C_EXPLOSION_M, alpha),
                         (cx - r_mid, cy - r_mid,
                          r_mid * 2, r_mid * 2))
        # Center core
        r_in = int(6 + pulse * 2)
        pygame.draw.rect(surf, (*C_EXPLOSION_C, alpha),
                         (cx - r_in, cy - r_in, r_in * 2, r_in * 2))

        surface.blit(surf, (self.x, self.y))


class Bomb:
    """Timed bomb; propagates cross-shaped explosion on detonation."""

    def __init__(self, col: int, row: int, owner, blast_range: int):
        self.col         = col
        self.row         = row
        self.owner       = owner     # Player reference
        self.blast_range = blast_range
        self.alive       = True
        self.detonated   = False
        self._fuse       = BOMB_FUSE_MS
        self._t          = 0          # animation tick

    @property
    def pixel_rect(self) -> pygame.Rect:
        return pygame.Rect(self.col * TILE_SIZE, self.row * TILE_SIZE,
                           TILE_SIZE, TILE_SIZE)

    def trigger(self):
        """Force instant detonation (chain reaction)."""
        self._fuse = 0

    def update(self, dt: int, game_map, all_players: list,
               all_bombs: list) -> list:
        """
        Returns a list of new Explosion objects when detonation occurs,
        otherwise returns an empty list.
        """
        self._t += 3
        self._fuse -= dt

        if self._fuse <= 0 and not self.detonated:
            return self._explode(game_map, all_players, all_bombs)
        return []

    def _explode(self, game_map, all_players: list,
                 all_bombs: list) -> list:
        self.detonated = True
        self.alive     = False
        self.owner.bombs_placed = max(0, self.owner.bombs_placed - 1)

        explosions: list[Explosion] = []
        DIRS = [(0, -1, 'tip_up', 'mid'),
                (0,  1, 'tip_down', 'mid'),
                (-1, 0, 'tip_left', 'mid'),
                (1,  0, 'tip_right', 'mid')]

        # Center
        explosions.append(Explosion(self.col, self.row, 'center'))
        self._hit_entities(self.col, self.row, all_players)

        for dx, dy, tip_kind, mid_kind in DIRS:
            for step in range(1, self.blast_range + 1):
                nc, nr = self.col + dx * step, self.row + dy * step
                tile = game_map.get_tile(nc, nr)

                if tile == WALL_SOLID:
                    break   # solid blocks propagation

                kind = tip_kind if step == self.blast_range else mid_kind
                explosions.append(Explosion(nc, nr, kind))
                self._hit_entities(nc, nr, all_players)

                # Chain: trigger any bomb on this tile
                for b in all_bombs:
                    if b is not self and b.alive and b.col == nc and b.row == nr:
                        b.trigger()

                if tile == WALL_SOFT:
                    game_map.destroy_wall(nc, nr)
                    break   # soft wall stops propagation after destruction

        return explosions

    @staticmethod
    def _hit_entities(col: int, row: int, all_players: list):
        blast_rect = pygame.Rect(col * TILE_SIZE, row * TILE_SIZE,
                                 TILE_SIZE, TILE_SIZE)
        for p in all_players:
            if p.alive:
                if blast_rect.colliderect(p.get_rect()):
                    p.take_damage()

    def draw(self, surface: pygame.Surface):
        import math
        # Pulsing bomb body
        pulse = abs(math.sin(math.radians(self._t * 2))) * 0.15
        fuse_pct = self._fuse / BOMB_FUSE_MS
        size = int(TILE_SIZE * (0.65 + 0.1 * (1 - fuse_pct) + pulse))
        x = self.col * TILE_SIZE + (TILE_SIZE - size) // 2
        y = self.row * TILE_SIZE + (TILE_SIZE - size) // 2

        pygame.draw.ellipse(surface, C_BOMB, (x, y, size, size))
        pygame.draw.ellipse(surface, (60, 60, 60), (x + 2, y + 2, size - 4, size // 3))

        # Fuse spark
        fuse_len = int(10 * fuse_pct) + 2
        cx = self.col * TILE_SIZE + TILE_SIZE // 2
        cy = int(y) - 2
        pygame.draw.line(surface, C_BOMB_GLOW,
                         (cx, cy), (cx + fuse_len, cy - fuse_len), 2)
        spark_alpha = int(abs(math.sin(math.radians(self._t * 8))) * 255)
        spark_surf = pygame.Surface((6, 6), pygame.SRCALPHA)
        pygame.draw.circle(spark_surf, (*C_EXPLOSION_C, spark_alpha), (3, 3), 3)
        surface.blit(spark_surf, (cx + fuse_len - 3, cy - fuse_len - 3))
