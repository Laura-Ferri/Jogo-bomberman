# pyrefly: ignore [missing-import]
import pygame
import random
from settings import (
    GRID_W, GRID_H, EMPTY, WALL_SOLID, WALL_SOFT, TILE_SIZE,
    C_FLOOR, C_FLOOR_ALT, C_WALL_SOLID, C_WALL_SOLID_H,
    C_WALL_SOFT, C_WALL_SOFT_H, C_WALL_SOFT_D, POWERUP_CHANCE
)
from powerup import PowerUp


class GameMap:
    """Grid-based map: generates, renders and manages tile state."""

    def __init__(self):
        self.powerups: list[PowerUp] = []
        self.grid: list[list[int]] = []
        self._generate()

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------
    def _generate(self):
        self.powerups.clear()
        self.grid = []

        for row in range(GRID_H):
            r = []
            for col in range(GRID_W):
                if row == 0 or row == GRID_H - 1 or col == 0 or col == GRID_W - 1:
                    r.append(WALL_SOLID)
                elif row % 2 == 0 and col % 2 == 0:
                    r.append(WALL_SOLID)
                else:
                    r.append(EMPTY)
            self.grid.append(r)

        # Corners kept clear for player spawns (2-tile radius)
        safe = set()
        for cc, cr in [(1, 1), (GRID_W - 2, 1),
                       (1, GRID_H - 2), (GRID_W - 2, GRID_H - 2)]:
            for dc in range(3):
                for dr in range(3):
                    safe.add((cc + dc - 1, cr + dr - 1))
                    safe.add((cc - dc + 1, cr - dr + 1))

        for row in range(1, GRID_H - 1):
            for col in range(1, GRID_W - 1):
                if self.grid[row][col] == EMPTY and (col, row) not in safe:
                    if random.random() < 0.62:
                        self.grid[row][col] = WALL_SOFT

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------
    def get_tile(self, col: int, row: int) -> int:
        if 0 <= row < GRID_H and 0 <= col < GRID_W:
            return self.grid[row][col]
        return WALL_SOLID

    def set_tile(self, col: int, row: int, tile_type: int):
        if 0 <= row < GRID_H and 0 <= col < GRID_W:
            self.grid[row][col] = tile_type

    def is_walkable(self, col: int, row: int) -> bool:
        return self.get_tile(col, row) == EMPTY

    def destroy_wall(self, col: int, row: int) -> bool:
        """Destroy soft wall; may spawn power-up. Returns True if destroyed."""
        if self.get_tile(col, row) == WALL_SOFT:
            self.set_tile(col, row, EMPTY)
            if random.random() < POWERUP_CHANCE:
                self.powerups.append(PowerUp(col, row))
            return True
        return False

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface):
        for row in range(GRID_H):
            for col in range(GRID_W):
                x = col * TILE_SIZE
                y = row * TILE_SIZE
                tile = self.grid[row][col]

                if tile == EMPTY:
                    color = C_FLOOR if (row + col) % 2 == 0 else C_FLOOR_ALT
                    pygame.draw.rect(surface, color, (x, y, TILE_SIZE, TILE_SIZE))

                elif tile == WALL_SOLID:
                    pygame.draw.rect(surface, C_WALL_SOLID,
                                     (x, y, TILE_SIZE, TILE_SIZE))
                    pygame.draw.rect(surface, C_WALL_SOLID_H,
                                     (x, y, TILE_SIZE, 5))
                    pygame.draw.rect(surface, (16, 22, 35),
                                     (x, y + TILE_SIZE - 4, TILE_SIZE, 4))
                    pygame.draw.rect(surface, (22, 30, 46),
                                     (x, y, 4, TILE_SIZE))

                elif tile == WALL_SOFT:
                    pygame.draw.rect(surface, C_WALL_SOFT,
                                     (x, y, TILE_SIZE, TILE_SIZE))
                    pygame.draw.rect(surface, C_WALL_SOFT_H,
                                     (x, y, TILE_SIZE, 5))
                    pygame.draw.rect(surface, C_WALL_SOFT_D,
                                     (x, y + TILE_SIZE - 4, TILE_SIZE, 4))
                    # Brick lines
                    mid = TILE_SIZE // 2
                    pygame.draw.line(surface, C_WALL_SOFT_D,
                                     (x, y + mid), (x + TILE_SIZE, y + mid), 2)
                    pygame.draw.line(surface, C_WALL_SOFT_D,
                                     (x + mid, y), (x + mid, y + mid), 2)
                    pygame.draw.line(surface, C_WALL_SOFT_D,
                                     (x, y + mid + mid // 2),
                                     (x + mid, y + mid + mid // 2), 2)

        # Power-ups on top
        for pu in self.powerups:
            pu.draw(surface)
