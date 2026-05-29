# pyrefly: ignore [missing-import]
import pygame
from settings import (
    GRID_W, GRID_H, TILE_SIZE, PLAYER_LIVES, PLAYER_SPEED,
    PLAYER_RANGE, PLAYER_BOMBS, HITBOX_SHRINK, RESPAWN_MS,
    CONTROLS, C_BLACK
)
from bomb import Bomb


# FSM States
IDLE      = 'idle'
MOVING    = 'moving'
DEAD      = 'dead'
RESPAWNING = 'respawning'


class Player:
    """Human-controlled Bomberman player."""

    # Spawn positions (col, row)
    SPAWNS = [
        (1, 1),
        (GRID_W - 2, GRID_H - 2),
        (1, GRID_H - 2),
        (GRID_W - 2, 1),
    ]

    def __init__(self, player_id: int, color: tuple):
        self.player_id   = player_id
        self.color       = color
        self.color_dark  = tuple(max(0, c - 60) for c in color)
        self.color_light = tuple(min(255, c + 60) for c in color)

        # Position (pixel, top-left of tile)
        sc, sr      = self.SPAWNS[player_id]
        self.px     = float(sc * TILE_SIZE)
        self.py     = float(sr * TILE_SIZE)

        # Stats
        self.lives        = PLAYER_LIVES
        self.score        = 0
        self.speed        = PLAYER_SPEED
        self.blast_range  = PLAYER_RANGE
        self.max_bombs    = PLAYER_BOMBS
        self.bombs_placed = 0

        # State machine
        self.state         = IDLE
        self.alive         = True
        self._respawn_t    = 0
        self._inv_t        = 0         # invincibility after respawn
        self._anim_t       = 0
        self._facing       = (0, 1)    # last movement direction

        # Bombs this player placed — tracked as objects for pixel-overlap check
        self._own_bombs: list = []

        # Death animation
        self._death_t = 0

        # Edge-trigger para colocação de bomba (evita auto-repeat do get_pressed)
        self._bomb_was_pressed = False

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------
    @property
    def col(self) -> int:
        return int(self.px + TILE_SIZE // 2) // TILE_SIZE

    @property
    def row(self) -> int:
        return int(self.py + TILE_SIZE // 2) // TILE_SIZE

    def get_rect(self) -> pygame.Rect:
        s = HITBOX_SHRINK
        return pygame.Rect(self.px + s, self.py + s,
                           TILE_SIZE - s * 2, TILE_SIZE - s * 2)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def take_damage(self):
        if self.state in (DEAD, RESPAWNING) or self._inv_t > 0:
            return
        self.lives -= 1
        if self.lives <= 0:
            self.alive = False
            self.state = DEAD
            self._death_t = 800
        else:
            self.state    = RESPAWNING
            self._respawn_t = RESPAWN_MS
            self._inv_t   = 2000

    def apply_powerup(self, pu):
        from powerup import RANGE_UP, SPEED_UP, EXTRA_BOMB
        if pu.type == RANGE_UP:
            self.blast_range += 1
        elif pu.type == SPEED_UP:
            self.speed = min(self.speed + 0.8, 6.0)
        elif pu.type == EXTRA_BOMB:
            self.max_bombs += 1

    def can_place_bomb(self) -> bool:
        return self.bombs_placed < self.max_bombs

    def place_bomb(self) -> Bomb | None:
        if not self.can_place_bomb():
            return None
        b = Bomb(self.col, self.row, self, self.blast_range)
        self.bombs_placed += 1
        # Track own bomb so player can walk out of its tile
        self._own_bombs.append(b)
        return b

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self, dt: int, keys, game_map, all_bombs: list) -> Bomb | None:
        self._anim_t += dt
        new_bomb = None

        if self._inv_t > 0:
            self._inv_t -= dt

        if self.state == DEAD:
            self._death_t -= dt
            return None

        if self.state == RESPAWNING:
            self._respawn_t -= dt
            if self._respawn_t <= 0:
                sc, sr = self.SPAWNS[self.player_id]
                self.px, self.py = float(sc * TILE_SIZE), float(sr * TILE_SIZE)
                self.state  = IDLE
                self._inv_t = 2000
            return None

        # --- Movimento ---
        ctrl = CONTROLS.get(self.player_id, {})
        dx, dy = 0, 0
        if keys[ctrl.get('up',    -1)]: dy = -1
        elif keys[ctrl.get('down', -1)]: dy = 1
        elif keys[ctrl.get('left', -1)]: dx = -1
        elif keys[ctrl.get('right',-1)]: dx = 1

        if dx != 0 or dy != 0:
            self._facing = (dx, dy)
            self._move(dx, dy, game_map, all_bombs)
            self.state = MOVING
        else:
            self.state = IDLE

        # --- Colocação de bomba (edge-triggered: apenas no primeiro frame do press) ---
        bomb_key = ctrl.get('bomb', -1)
        bomb_pressed = keys[bomb_key]
        if bomb_pressed and not self._bomb_was_pressed:
            new_bomb = self.place_bomb()
        self._bomb_was_pressed = bomb_pressed

        return new_bomb

    def _move(self, dx: int, dy: int, game_map, all_bombs: list):
        step = self.speed

        # --- Passthrough na própria bomba ---
        player_rect = self.get_rect()
        passthrough: set[tuple] = set()
        still_overlapping: list = []

        for b in self._own_bombs:
            if not b.alive:
                continue
            bomb_area = pygame.Rect(
                b.col * TILE_SIZE, b.row * TILE_SIZE, TILE_SIZE, TILE_SIZE
            )
            if player_rect.colliderect(bomb_area):
                passthrough.add((b.col, b.row))
                still_overlapping.append(b)

        self._own_bombs = still_overlapping

        bomb_tiles = {
            (b.col, b.row) for b in all_bombs if (b.col, b.row) not in passthrough
        }

        s = HITBOX_SHRINK

        def blocked(px: float, py: float) -> bool:
            for cx2 in [px + s, px + TILE_SIZE - s - 1]:
                for cy2 in [py + s, py + TILE_SIZE - s - 1]:
                    tc = int(cx2) // TILE_SIZE
                    tr = int(cy2) // TILE_SIZE
                    if not game_map.is_walkable(tc, tr) or (tc, tr) in bomb_tiles:
                        return True
            return False

        # --- Auto-alinhamento de corredor ---
        # Quando move em Y mas está desalinhado do centro do tile em X,
        # desliza suavemente para o centro (e vice-versa). Elimina travamentos.
        ALIGN_SPEED = min(step, 2.0)   # velocidade do deslize lateral
        ALIGN_THRESHOLD = TILE_SIZE // 2  # só alinha se próximo ao centro

        new_px = self.px + dx * step
        new_py = self.py + dy * step

        # Movimento X
        if dx != 0:
            if not blocked(new_px, self.py):
                self.px = new_px
            else:
                # Tenta deslizar em Y para desencavar do canto
                tile_cy = (self.row * TILE_SIZE)
                off = self.py - tile_cy
                if 0 < abs(off) <= ALIGN_THRESHOLD:
                    nudge = ALIGN_SPEED if off < 0 else -ALIGN_SPEED
                    if not blocked(self.px, self.py + nudge):
                        self.py = self.py + nudge

        # Movimento Y
        if dy != 0:
            if not blocked(self.px, new_py):
                self.py = new_py
            else:
                # Tenta deslizar em X para desencavar do canto
                tile_cx = (self.col * TILE_SIZE)
                off = self.px - tile_cx
                if 0 < abs(off) <= ALIGN_THRESHOLD:
                    nudge = ALIGN_SPEED if off < 0 else -ALIGN_SPEED
                    if not blocked(self.px + nudge, self.py):
                        self.px = self.px + nudge

        # Clamp dentro da área jogável
        self.px = max(TILE_SIZE, min((GRID_W - 2) * TILE_SIZE, self.px))
        self.py = max(TILE_SIZE, min((GRID_H - 2) * TILE_SIZE, self.py))

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface):
        if self.state == DEAD and self._death_t <= 0:
            return

        # Blink during invincibility
        if self._inv_t > 0 and (self._inv_t // 150) % 2 == 0:
            return

        x = int(self.px)
        y = int(self.py)
        s = TILE_SIZE
        cx, cy = x + s // 2, y + s // 2

        # Death shrink animation
        if self.state == DEAD:
            scale = max(0.0, self._death_t / 800)
            s = int(s * scale)
            cx, cy = x + TILE_SIZE // 2, y + TILE_SIZE // 2
            x = cx - s // 2
            y = cy - s // 2

        if s < 4:
            return

        # --- Body ---
        body_rect = pygame.Rect(x + s // 5, y + s // 3, s * 3 // 5, s * 2 // 3)
        pygame.draw.ellipse(surface, self.color, body_rect)
        pygame.draw.ellipse(surface, self.color_dark, body_rect, 2)

        # --- Head ---
        head_r = s // 4
        head_x = cx
        head_y = y + s // 4
        pygame.draw.circle(surface, self.color_light, (head_x, head_y), head_r)
        pygame.draw.circle(surface, self.color_dark,  (head_x, head_y), head_r, 2)

        # --- Eyes (direction-aware) ---
        fx, fy = self._facing
        eye_off = head_r // 2
        if fx == 0 and fy == 0:
            fx, fy = 0, 1
        eye1 = (head_x - eye_off // 2 + fx * 2, head_y + fy * 2)
        eye2 = (head_x + eye_off // 2 + fx * 2, head_y + fy * 2)
        for ex, ey in [eye1, eye2]:
            pygame.draw.circle(surface, C_BLACK, (ex, ey), 2)

        # --- Legs (walk animation) ---
        walk_frame = int(self._anim_t / 100) % 4
        leg_swing = [3, 0, -3, 0][walk_frame] if self.state == MOVING else 0
        leg_y = y + s - 4
        pygame.draw.line(surface, self.color_dark,
                         (cx - 6, leg_y - 6), (cx - 6, leg_y + leg_swing), 3)
        pygame.draw.line(surface, self.color_dark,
                         (cx + 6, leg_y - 6), (cx + 6, leg_y - leg_swing), 3)
