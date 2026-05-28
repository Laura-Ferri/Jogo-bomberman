# pyrefly: ignore [missing-import]
import pygame
import random
from collections import deque
from settings import DIFFICULTY, TILE_SIZE, GRID_W, GRID_H, HITBOX_SHRINK, WALL_SOFT
from player import Player, DEAD, RESPAWNING, IDLE, MOVING
from bomb import Bomb

# FSM states
WANDER = 'wander'
HUNT   = 'hunt'
BOMB   = 'bomb_state'
FLEE   = 'flee'

# How many tiles ahead the bot tries to path during wander
WANDER_STEPS = 5


class Bot(Player):
    """
    AI-controlled bot.

    FSM priority (checked every _interval ms):
        FLEE > BOMB > HUNT > WANDER

    Movement: Continuous every frame — path is refreshed
    automatically when exhausted so the bot never stands still.
    """

    def __init__(self, player_id: int, color: tuple, difficulty: str = 'medium'):
        super().__init__(player_id, color)
        cfg               = DIFFICULTY[difficulty]
        self._interval    = cfg['interval']       # ms between strategy decisions
        self._flee_margin = cfg['flee_margin']    # ms before explosion to flee
        self._ai_timer    = random.randint(0, cfg['interval'])  # stagger start
        self._ai_state    = WANDER
        self._path: list  = []

    # ------------------------------------------------------------------
    # Override update — AI drives movement instead of keyboard
    # ------------------------------------------------------------------
    def update(self, dt: int, keys, game_map, all_bombs: list,
               all_players: list | None = None) -> Bomb | None:
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

        self._ai_timer -= dt

        # Re-decide strategy on timer expiry OR when the path is empty
        # (so the bot immediately picks a new direction after reaching a tile)
        if self._ai_timer <= 0 or not self._path:
            self._ai_timer = self._interval
            self._decide(game_map, all_bombs, all_players or [])

        # Execute movement every frame regardless of state
        if self._ai_state == FLEE:
            self._execute_move(game_map, all_bombs)
        elif self._ai_state == BOMB:
            new_bomb = self._execute_bomb(game_map, all_bombs)
        elif self._ai_state == HUNT:
            self._execute_move(game_map, all_bombs)
        else:  # WANDER
            self._execute_move(game_map, all_bombs)

        return new_bomb

    # ------------------------------------------------------------------
    # Strategy decision (called on timer or when path empties)
    # ------------------------------------------------------------------
    def _decide(self, game_map, all_bombs: list, all_players: list):
        # P1: Flee if any bomb threatens us
        if self._is_threatened(all_bombs):
            self._ai_state = FLEE
            self._path = self._bfs_safe(game_map, all_bombs)
            if not self._path:                       # already safe — wander
                self._ai_state = WANDER
                self._path = self._pick_wander_path(game_map, all_bombs)
            return

        # P2: Plant bomb when next to a target
        if self.can_place_bomb() and self._has_bomb_target(game_map, all_players):
            if self._safe_to_bomb(game_map, all_bombs):
                self._ai_state = BOMB
                return

        # P3: Hunt nearest human
        human = self._nearest_human(all_players)
        if human:
            dest = (human.col, human.row)
            path = self._bfs(game_map, all_bombs, dest)
            if path:
                self._path     = path
                self._ai_state = HUNT
                return

        # P4: Wander continuously
        self._ai_state = WANDER
        if not self._path:
            self._path = self._pick_wander_path(game_map, all_bombs)

    # ------------------------------------------------------------------
    # Movement execution (shared by WANDER / HUNT / FLEE)
    # ------------------------------------------------------------------
    def _execute_move(self, game_map, all_bombs: list):
        """Walk along self._path; if empty pick a new wander path."""
        if not self._path:
            self._path = self._pick_wander_path(game_map, all_bombs)
        if self._path:
            self._walk_toward(self._path[0], game_map, all_bombs)
            # Pop waypoint when bot reaches it
            tc, tr = self._path[0]
            if abs(self.px - tc * TILE_SIZE) < self.speed + 1 and \
               abs(self.py - tr * TILE_SIZE) < self.speed + 1:
                self.px = float(tc * TILE_SIZE)
                self.py = float(tr * TILE_SIZE)
                self._path.pop(0)

    def _execute_bomb(self, game_map, all_bombs: list) -> Bomb | None:
        """Plant a bomb then immediately flee."""
        bomb = self.place_bomb()
        self._ai_state = FLEE
        self._path = self._bfs_safe(game_map, all_bombs)
        if not self._path:
            self._path = self._pick_wander_path(game_map, all_bombs)
        return bomb

    # ------------------------------------------------------------------
    # Low-level movement toward a target pixel tile
    # ------------------------------------------------------------------
    def _walk_toward(self, target: tuple, game_map, all_bombs: list):
        tc, tr = target
        tx = float(tc * TILE_SIZE)
        ty = float(tr * TILE_SIZE)
        dx = tx - self.px
        dy = ty - self.py
        dist = (dx * dx + dy * dy) ** 0.5
        if dist < 1:
            return
        nx = dx / dist
        ny = dy / dist
        self._facing = (int(round(nx)), int(round(ny)))
        self._move_bot(nx * self.speed, ny * self.speed, game_map, all_bombs)

    def _move_bot(self, vx: float, vy: float, game_map, all_bombs: list):
        """Axis-separated movement with wall + bomb collision."""
        # Own-bomb passthrough so the bot can escape the tile where it just planted
        bot_rect = self.get_rect()
        passthrough: set[tuple] = set()
        still_overlapping: list = []

        for b in getattr(self, '_own_bombs', []):
            if not b.alive:
                continue
            bomb_area = pygame.Rect(b.col * TILE_SIZE, b.row * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            if bot_rect.colliderect(bomb_area):
                passthrough.add((b.col, b.row))
                still_overlapping.append(b)
        self._own_bombs = still_overlapping

        bomb_tiles = {(b.col, b.row) for b in all_bombs if (b.col, b.row) not in passthrough}
        s = HITBOX_SHRINK

        def blocked(px: float, py: float) -> bool:
            for cx2 in [px + s, px + TILE_SIZE - s - 1]:
                for cy2 in [py + s, py + TILE_SIZE - s - 1]:
                    tc = int(cx2) // TILE_SIZE
                    tr = int(cy2) // TILE_SIZE
                    if not game_map.is_walkable(tc, tr) or (tc, tr) in bomb_tiles:
                        return True
            return False

        new_px = self.px + vx
        new_py = self.py + vy

        if not blocked(new_px, self.py):
            self.px = new_px
        if not blocked(self.px, new_py):
            self.py = new_py

        # Clamp inside playable area
        self.px = max(TILE_SIZE, min((GRID_W - 2) * TILE_SIZE, self.px))
        self.py = max(TILE_SIZE, min((GRID_H - 2) * TILE_SIZE, self.py))
        self.state = IDLE if (vx == 0 and vy == 0) else MOVING

    def _safe_to_bomb(self, game_map, all_bombs: list) -> bool:
        """Simulate placing a bomb to see if we have a valid escape route."""
        # Create a phantom bomb
        phantom = Bomb(self.col, self.row, self, self.blast_range)
        simulated_bombs = all_bombs + [phantom]
        escape_path = self._bfs_safe(game_map, simulated_bombs)
        return bool(escape_path)

    # ------------------------------------------------------------------
    # Wander path generator — picks a random multi-step walkable path
    # ------------------------------------------------------------------
    def _pick_wander_path(self, game_map, all_bombs: list) -> list:
        """
        Build a path of up to WANDER_STEPS tiles by randomly walking
        from the bot's current grid position.
        """
        bomb_tiles = {(b.col, b.row) for b in all_bombs}
        dirs       = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        path       = []
        col, row   = self.col, self.row

        for _ in range(WANDER_STEPS):
            candidates = []
            random.shuffle(dirs)
            for dc, dr in dirs:
                nc, nr = col + dc, row + dr
                if game_map.is_walkable(nc, nr) and (nc, nr) not in bomb_tiles:
                    candidates.append((nc, nr))
            if not candidates:
                break
            col, row = candidates[0]
            path.append((col, row))

        return path

    # ------------------------------------------------------------------
    # Threat detection
    # ------------------------------------------------------------------
    def _is_threatened(self, all_bombs: list) -> bool:
        for b in all_bombs:
            if not b.alive:
                continue
            if b._fuse > self._flee_margin:
                continue
            if self._in_blast(self.col, self.row, b):
                return True
        return False

    @staticmethod
    def _in_blast(col: int, row: int, bomb: Bomb) -> bool:
        if bomb.col == col and abs(bomb.row - row) <= bomb.blast_range:
            return True
        if bomb.row == row and abs(bomb.col - col) <= bomb.blast_range:
            return True
        return False

    def _has_bomb_target(self, game_map, all_players: list) -> bool:
        for dc, dr in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            if game_map.get_tile(self.col + dc, self.row + dr) == WALL_SOFT:
                return True
        human = self._nearest_human(all_players)
        if human:
            dist = abs(human.col - self.col) + abs(human.row - self.row)
            if dist <= self.blast_range:
                return True
        return False

    def _nearest_human(self, all_players: list):
        humans = [
            p for p in all_players
            if not isinstance(p, Bot)
            and p.alive
            and p.state not in (DEAD, RESPAWNING)
        ]
        if not humans:
            return None
        return min(humans,
                   key=lambda p: abs(p.col - self.col) + abs(p.row - self.row))

    # ------------------------------------------------------------------
    # BFS helpers
    # ------------------------------------------------------------------
    def _bfs(self, game_map, all_bombs: list, target: tuple) -> list:
        """Return shortest walkable path from current pos to target."""
        bomb_tiles = {(b.col, b.row) for b in all_bombs}
        start      = (self.col, self.row)
        if start == target:
            return []
        visited = {start}
        queue   = deque([(start, [])])
        for dc, dr in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            pass  # just warming up the pattern

        dirs = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        while queue:
            pos, path = queue.popleft()
            for dc, dr in dirs:
                npos = (pos[0] + dc, pos[1] + dr)
                if npos in visited:
                    continue
                if not game_map.is_walkable(npos[0], npos[1]):
                    continue
                if npos in bomb_tiles:
                    continue
                new_path = path + [npos]
                if npos == target:
                    return new_path
                visited.add(npos)
                queue.append((npos, new_path))
        return []

    def _bfs_safe(self, game_map, all_bombs: list) -> list:
        """Return shortest path to the nearest tile not in any blast radius."""
        dangerous = self._blast_tiles(all_bombs)
        start     = (self.col, self.row)
        visited   = {start}
        queue     = deque([(start, [])])
        dirs      = [(0, -1), (0, 1), (-1, 0), (1, 0)]

        while queue:
            pos, path = queue.popleft()
            if pos not in dangerous:
                return path
            for dc, dr in dirs:
                npos = (pos[0] + dc, pos[1] + dr)
                if npos in visited:
                    continue
                if not game_map.is_walkable(npos[0], npos[1]):
                    continue
                visited.add(npos)
                queue.append((npos, path + [npos]))
        return []

    @staticmethod
    def _blast_tiles(all_bombs: list) -> set:
        danger = set()
        for b in all_bombs:
            if not b.alive:
                continue
            danger.add((b.col, b.row))
            for dc, dr in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                for s in range(1, b.blast_range + 1):
                    danger.add((b.col + dc * s, b.row + dr * s))
        return danger
