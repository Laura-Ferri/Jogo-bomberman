# pyrefly: ignore [missing-import]
import pygame
import random
from collections import deque
from settings import DIFFICULTY, TILE_SIZE, GRID_W, GRID_H, HITBOX_SHRINK, WALL_SOFT, PLAYER_SPEED
from player import Player, DEAD, RESPAWNING, IDLE, MOVING
from bomb import Bomb

# FSM states
WANDER = 'wander'
HUNT   = 'hunt'
BOMB   = 'bomb_state'
FLEE   = 'flee'
PICKUP = 'pickup'  # estado exclusivo do Hard: ir buscar power-up

# Quantos tiles aleatórios o bot tenta durante o wander
WANDER_STEPS = 5


class Bot(Player):
    """
    AI-controlled bot (FSM + BFS).

    Prioridade FSM (checada a cada _interval ms):
        FLEE > BOMB > HUNT/PICKUP > WANDER

    Hard mode adiciona:
        - Velocidade 20% acima do jogador
        - Caça ativa mesmo sem caminho livre imediato (BFS mais amplo)
        - Previsão de encurralamento antes de soltar bomba
        - Coleta de power-ups próximos quando ocioso
    """

    def __init__(self, player_id: int, color: tuple, difficulty: str = 'medium'):
        super().__init__(player_id, color)
        cfg = DIFFICULTY[difficulty]
        self._difficulty      = difficulty
        self._interval        = cfg['interval']
        self._flee_margin     = cfg['flee_margin']
        self._aggression_range = cfg['aggression_range']
        # Aplicar multiplicador de velocidade sobre a base do Player
        self.speed            = PLAYER_SPEED * cfg['speed_mult']
        self._ai_timer        = random.randint(0, cfg['interval'])  # stagger inicial
        self._ai_state        = WANDER
        self._path: list      = []
        # Referência à bomba reciém-plantada; limpa quando explode
        self._post_bomb: Bomb | None = None

    # ------------------------------------------------------------------
    # Override update — IA dirige o movimento ao invés do teclado
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

        # Limpa rastreador quando a bomba própria explodir
        if self._post_bomb is not None and not self._post_bomb.alive:
            self._post_bomb = None

        # ── Detecção de ameaça a CADA frame — sempre interrompe para fugir
        if self._is_threatened(all_bombs):
            if self._ai_state != FLEE or not self._path:
                self._ai_state = FLEE
                self._path = self._bfs_safe(game_map, all_bombs)
                if not self._path:
                    self._path = self._pick_wander_path(game_map, all_bombs)
        elif self._ai_timer <= 0 or not self._path:
            self._ai_timer = self._interval
            # Não interrompe path de fuga ativo (causa freeze mid-escape)
            if self._ai_state == FLEE and self._path:
                pass  # bot continua a fuga, não redireciona
            elif (self._post_bomb is not None and self._post_bomb.alive
                    and self._difficulty == 'medium'):
                # Medium: aguarda seguro até bomba explodir
                if not self._path:
                    self._hold_safe_position(game_map, all_bombs)
            else:
                # Hard e Easy: decisão normal (Hunt evita blast zones via BFS)
                self._decide(game_map, all_bombs, all_players or [])

        # Executar ação do estado atual
        if self._ai_state == FLEE:
            self._execute_move(game_map, all_bombs)
        elif self._ai_state == BOMB:
            new_bomb = self._execute_bomb(game_map, all_bombs)
        elif self._ai_state in (HUNT, PICKUP):
            self._execute_move(game_map, all_bombs)
        else:  # WANDER
            self._execute_move(game_map, all_bombs)

        return new_bomb

    # ------------------------------------------------------------------
    # Decisão estratégica (chamada no timer ou quando o path zera)
    # ------------------------------------------------------------------
    def _decide(self, game_map, all_bombs: list, all_players: list):
        # P1: Fugir se houver bomba ameaçando
        if self._is_threatened(all_bombs):
            self._ai_state = FLEE
            self._path = self._bfs_safe(game_map, all_bombs)
            if not self._path:
                self._ai_state = WANDER
                self._path = self._pick_wander_path(game_map, all_bombs)
            return

        # P2: Soltar bomba quando há alvo
        if self.can_place_bomb() and self._has_bomb_target(game_map, all_players):
            safe = self._safe_to_bomb(game_map, all_bombs)
            trap = (self._difficulty == 'hard' and
                    self._will_trap_target(game_map, all_bombs, all_players))
            if safe or trap:
                self._ai_state = BOMB
                return

        # P3: Caçar humano mais próximo (Hard: sempre; outros: fallback)
        human = self._nearest_human(all_players)
        if human:
            dest = (human.col, human.row)
            path = self._bfs(game_map, all_bombs, dest)
            if path:
                self._path     = path
                self._ai_state = HUNT
                return

        # P4 (Hard): Coletar power-up próximo quando não há humano acessível
        if self._difficulty == 'hard':
            pu_path = self._path_to_nearest_powerup(game_map, all_bombs)
            if pu_path:
                self._path     = pu_path
                self._ai_state = PICKUP
                return

        # P5: Vagar
        self._ai_state = WANDER
        if not self._path:
            self._path = self._pick_wander_path(game_map, all_bombs)

    # ------------------------------------------------------------------
    # Execução de movimento (WANDER / HUNT / FLEE / PICKUP)
    # ------------------------------------------------------------------
    def _execute_move(self, game_map, all_bombs: list):
        """Segue self._path; se vazio, escolhe wander ou fica parado."""
        if not self._path:
            # Pós-bomba Hard/Medium: não vaga de volta para a zona de perigo
            if (self._post_bomb is not None and self._post_bomb.alive
                    and self._difficulty in ('hard', 'medium')):
                self.state = IDLE   # fica parado no tile seguro
                return
            self._path = self._pick_wander_path(game_map, all_bombs)
        if self._path:
            self._walk_toward(self._path[0], game_map, all_bombs)
            tc, tr = self._path[0]
            if (abs(self.px - tc * TILE_SIZE) < self.speed + 1 and
                    abs(self.py - tr * TILE_SIZE) < self.speed + 1):
                self.px = float(tc * TILE_SIZE)
                self.py = float(tr * TILE_SIZE)
                self._path.pop(0)

    def _execute_bomb(self, game_map, all_bombs: list) -> Bomb | None:
        """Planta bomba, rastreia em _post_bomb e calcula fuga com a própria bomba inclusa."""
        bomb = self.place_bomb()
        if bomb:
            self._post_bomb = bomb          # rastreia para bloquear reengajamento
        self._ai_state = FLEE
        # Inclui a bomba reciém-plantada na simulação de fuga (anti-suicídio)
        sim_bombs = all_bombs + ([bomb] if bomb else [])
        self._path = self._bfs_safe(game_map, sim_bombs)
        if not self._path:
            self._path = self._pick_wander_path(game_map, all_bombs)
        return bomb

    def _hold_safe_position(self, game_map, all_bombs: list):
        """
        Chamado quando bomba própria está ativa e dificuldade é Hard/Medium.
        Hard: fica parado na posição segura (path vazio).
        Medium: pequeno wander seguro evitando blast zone.
        """
        self._ai_state = FLEE  # mantém estado de fuga para não chamar _decide
        if self._difficulty == 'hard':
            self._path = []      # caminho vazio = bot fica parado
        else:                    # medium
            self._path = self._pick_safe_wander(game_map, all_bombs)

    def _pick_safe_wander(self, game_map, all_bombs: list) -> list:
        """Wander curto que nunca entra em tile perigoso (ciente de paredes)."""
        dangerous  = self._blast_tiles(all_bombs, game_map)
        bomb_tiles = {(b.col, b.row) for b in all_bombs}
        dirs       = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        path       = []
        col, row   = self.col, self.row

        for _ in range(3):
            random.shuffle(dirs)
            candidates = [
                (col + dc, row + dr) for dc, dr in dirs
                if game_map.is_walkable(col + dc, row + dr)
                and (col + dc, row + dr) not in bomb_tiles
                and (col + dc, row + dr) not in dangerous
            ]
            if not candidates:
                break
            col, row = candidates[0]
            path.append((col, row))

        return path


    # ------------------------------------------------------------------
    # Movimentação de baixo nível em direção a um tile alvo
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
        """Movimento do bot: separação de eixos + passthrough + auto-alinhamento."""
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

        ALIGN_SPEED = min(abs(vx) + abs(vy), 2.0)
        ALIGN_THRESHOLD = TILE_SIZE // 2

        new_px = self.px + vx
        new_py = self.py + vy

        # Eixo X
        if vx != 0:
            if not blocked(new_px, self.py):
                self.px = new_px
            else:
                off = self.py - (self.row * TILE_SIZE)
                if 0 < abs(off) <= ALIGN_THRESHOLD:
                    nudge = ALIGN_SPEED if off < 0 else -ALIGN_SPEED
                    if not blocked(self.px, self.py + nudge):
                        self.py += nudge

        # Eixo Y
        if vy != 0:
            if not blocked(self.px, new_py):
                self.py = new_py
            else:
                off = self.px - (self.col * TILE_SIZE)
                if 0 < abs(off) <= ALIGN_THRESHOLD:
                    nudge = ALIGN_SPEED if off < 0 else -ALIGN_SPEED
                    if not blocked(self.px + nudge, self.py):
                        self.px += nudge

        # Manter dentro da área jogável
        self.px = max(TILE_SIZE, min((GRID_W - 2) * TILE_SIZE, self.px))
        self.py = max(TILE_SIZE, min((GRID_H - 2) * TILE_SIZE, self.py))
        self.state = IDLE if (vx == 0 and vy == 0) else MOVING

    # ------------------------------------------------------------------
    # Checagem de segurança para soltar bomba
    # ------------------------------------------------------------------
    def _safe_to_bomb(self, game_map, all_bombs: list) -> bool:
        """Simula colocar uma bomba e verifica se há rota de fuga."""
        phantom = Bomb(self.col, self.row, self, self.blast_range)
        simulated = all_bombs + [phantom]
        return bool(self._bfs_safe(game_map, simulated))

    def _will_trap_target(self, game_map, all_bombs: list, all_players: list) -> bool:
        """
        Hard mode: verifica se plantar uma bomba aqui encurrala o alvo
        (o alvo tem poucas ou nenhuma rota de fuga após a explosão).
        """
        human = self._nearest_human(all_players)
        if not human:
            return False
        phantom = Bomb(self.col, self.row, self, self.blast_range)
        simulated = all_bombs + [phantom]
        # Calcula rotas de fuga do humano com a bomba simulada
        escape = self._bfs_safe_from(game_map, simulated, human.col, human.row)
        # Se o humano tem ≤1 rota, vale a pena encurralar
        return len(escape) <= 1

    # ------------------------------------------------------------------
    # Wander path — caminho aleatório multi-passo
    # ------------------------------------------------------------------
    def _pick_wander_path(self, game_map, all_bombs: list) -> list:
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
    # Power-up seeking (Hard only)
    # ------------------------------------------------------------------
    def _path_to_nearest_powerup(self, game_map, all_bombs: list) -> list:
        """Retorna BFS path até o power-up mais próximo se estiver no alcance."""
        powerups = getattr(game_map, 'powerups', [])
        if not powerups:
            return []

        # Filtra power-ups vivos e dentro do alcance de agressividade
        candidates = [
            pu for pu in powerups
            if pu.alive and
            abs(pu.col - self.col) + abs(pu.row - self.row) <= self._aggression_range
        ]
        if not candidates:
            return []

        # Encontra o mais próximo por Manhattan e tenta BFS
        candidates.sort(key=lambda p: abs(p.col - self.col) + abs(p.row - self.row))
        for pu in candidates:
            path = self._bfs(game_map, all_bombs, (pu.col, pu.row))
            if path:
                return path
        return []

    # ------------------------------------------------------------------
    # Detecção de ameaça
    # ------------------------------------------------------------------
    def _is_threatened(self, all_bombs: list) -> bool:
        """Detecta se o bot está no raio de qualquer bomba ativa cuja fuse
        está abaixo de flee_margin. Hard tem flee_margin alto (2200ms),
        então reage muito antes que Easy (400ms)."""
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
        # Parede destrutível adjacente?
        for dc, dr in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            if game_map.get_tile(self.col + dc, self.row + dr) == WALL_SOFT:
                return True
        # Humano dentro do alcance de agressividade?
        human = self._nearest_human(all_players)
        if human:
            dist = abs(human.col - self.col) + abs(human.row - self.row)
            if dist <= self._aggression_range:
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
        return min(humans, key=lambda p: abs(p.col - self.col) + abs(p.row - self.row))

    # ------------------------------------------------------------------
    # BFS helpers
    # ------------------------------------------------------------------
    def _bfs(self, game_map, all_bombs: list, target: tuple) -> list:
        """Caminho mais curto até destino, evitando bomb tiles E blast zones ativas."""
        bomb_tiles = {(b.col, b.row) for b in all_bombs}
        dangerous  = self._blast_tiles(all_bombs, game_map)  # evita retornar à zona de perigo
        start      = (self.col, self.row)
        if start == target:
            return []
        visited = {start}
        queue   = deque([(start, [])])
        dirs    = [(0, -1), (0, 1), (-1, 0), (1, 0)]

        while queue:
            pos, path = queue.popleft()
            for dc, dr in dirs:
                npos = (pos[0] + dc, pos[1] + dr)
                if npos in visited:
                    continue
                if not game_map.is_walkable(npos[0], npos[1]):
                    continue
                if npos in bomb_tiles or npos in dangerous:
                    continue
                new_path = path + [npos]
                if npos == target:
                    return new_path
                visited.add(npos)
                queue.append((npos, new_path))
        return []

    def _bfs_safe(self, game_map, all_bombs: list) -> list:
        """Caminho até tile seguro, com passthrough apenas da própria bomba."""
        own_tiles = {(b.col, b.row) for b in self._own_bombs if b.alive}
        return self._bfs_safe_from(game_map, all_bombs, self.col, self.row, own_tiles)

    def _bfs_safe_from(self, game_map, all_bombs: list,
                       start_col: int, start_row: int,
                       own_passthrough: set | None = None) -> list:
        """BFS de fuga: passthrough apenas em tiles da própria bomba.
        Bombas inimigas são tratadas como obstáculos sólidos.
        """
        own_passthrough  = own_passthrough or set()
        dangerous        = self._blast_tiles(all_bombs, game_map)
        # Bloqueios: bombas que não são da lista de passthrough (bombas inimigas)
        solid_bomb_tiles = {
            (b.col, b.row) for b in all_bombs
            if b.alive and (b.col, b.row) not in own_passthrough
        }
        start   = (start_col, start_row)
        visited = {start}
        queue   = deque([(start, [])])
        dirs    = [(0, -1), (0, 1), (-1, 0), (1, 0)]

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
                if npos in solid_bomb_tiles:
                    continue  # não atravessa bombas inimigas
                visited.add(npos)
                queue.append((npos, path + [npos]))
        return []

    @staticmethod
    def _blast_tiles(all_bombs: list, game_map=None) -> set:
        """Calcula tiles em risco. Com game_map, para propagação em paredes."""
        from settings import WALL_SOLID, WALL_SOFT
        danger = set()
        for b in all_bombs:
            if not b.alive:
                continue
            danger.add((b.col, b.row))
            for dc, dr in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                for s in range(1, b.blast_range + 1):
                    nc, nr = b.col + dc * s, b.row + dr * s
                    if game_map is not None:
                        tile = game_map.get_tile(nc, nr)
                        if tile == WALL_SOLID:
                            break   # parede sólida bloqueia propagação
                        if tile == WALL_SOFT:
                            danger.add((nc, nr))  # parede mole é destruída, fica no perigo
                            break
                    danger.add((nc, nr))
        return danger
