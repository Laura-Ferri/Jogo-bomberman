import pygame
from settings import DEFAULT_VOLUME, PLAYER_COLORS
from map import GameMap
from player import Player, DEAD, RESPAWNING
from enemy import Bot
from bomb import Bomb, Explosion
from hud import HUD
from menu import PauseMenu, ResultScreen


class Game:
    """
    Core game coordinator.
    Manages the game loop: input → update → render.
    Modes: 'pvp' | 'coop'
    """

    def __init__(self, mode: str, player_colors: list[tuple],
                 difficulty: str = 'medium', volume: float = DEFAULT_VOLUME):
        self.mode       = mode
        self.difficulty = difficulty
        self.volume     = volume
        self.running    = True
        self.finished   = False
        self.paused     = False

        # Build entities
        self._map        = GameMap()
        self._players: list[Player] = []
        self._bots: list[Bot]       = []
        self._bombs: list[Bomb]     = []
        self._explosions: list[Explosion] = []

        self._pause_menu  = PauseMenu()
        self._result      = None
        self._result_data = None

        self._clock_ms = 0  # total elapsed

        self._setup_entities(player_colors)

        # Load sounds silently (no error if files missing)
        self._snd_bomb  = self._load_sound('assets/sounds/bomb.ogg')
        self._snd_exp   = self._load_sound('assets/sounds/explosion.ogg')
        self._snd_pu    = self._load_sound('assets/sounds/powerup.ogg')
        self._snd_death = self._load_sound('assets/sounds/death.ogg')

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def _setup_entities(self, player_colors: list[tuple]):
        if self.mode == 'pvp':
            for i, color in enumerate(player_colors):
                self._players.append(Player(i, color))
        elif self.mode == 'coop':
            # Aliados: mesma cor (do player 1)
            human_color = player_colors[0]
            for i, _ in enumerate(player_colors):
                self._players.append(Player(i, human_color))
            
            # Bots: cor diferente
            available_bot_colors = [c for c in PLAYER_COLORS if c != human_color]
            bot_colors = [available_bot_colors[0], available_bot_colors[1]]
            for j, bc in enumerate(bot_colors):
                self._bots.append(Bot(2 + j, bc, self.difficulty))

    @staticmethod
    def _generate_retro_sound(sound_type: str):
        """Gera sfx em memoria (8-bit style) se nao houver arquivo."""
        import io, wave, struct, random
        sample_rate = 22050
        duration_ms = 150
        vol = 0.3
        
        if sound_type == 'bomb':
            freq, wave_type = 400.0, 'square'
            duration_ms = 80
        elif sound_type == 'explosion':
            freq, wave_type = 100.0, 'noise'
            duration_ms = 350
        elif sound_type == 'powerup':
            freq, wave_type = 800.0, 'square'
            duration_ms = 200
        elif sound_type == 'death':
            freq, wave_type = 150.0, 'saw'
            duration_ms = 400
        else:
            return None

        num_samples = int(sample_rate * (duration_ms / 1000.0))
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sample_rate)
            samples = []
            for i in range(num_samples):
                t = float(i) / sample_rate
                
                # sweep frequency over time for death
                f = freq
                if sound_type == 'death':
                    f = freq * (1.0 - (i / num_samples))
                elif sound_type == 'powerup':
                    f = freq + (i % 2000) * 0.1
                
                if wave_type == 'square':
                    val = 1.0 if (t * f) % 1.0 < 0.5 else -1.0
                elif wave_type == 'noise':
                    val = random.uniform(-1.0, 1.0)
                else: # saw
                    val = 2.0 * ((t * f) % 1.0) - 1.0
                
                env = 1.0 - (i / num_samples) # fade out
                sample = int(val * env * vol * 32767)
                samples.append(struct.pack('<h', sample))
            w.writeframes(b''.join(samples))
        buf.seek(0)
        return pygame.mixer.Sound(buf)

    @staticmethod
    def _load_sound(path: str):
        try:
            snd = pygame.mixer.Sound(path)
            return snd
        except Exception:
            # Fallback for synthetic retro sounds!
            if 'bomb' in path: return Game._generate_retro_sound('bomb')
            if 'explosion' in path: return Game._generate_retro_sound('explosion')
            if 'powerup' in path: return Game._generate_retro_sound('powerup')
            if 'death' in path: return Game._generate_retro_sound('death')
            return None

    def _play(self, snd):
        if snd:
            snd.set_volume(self.volume)
            snd.play()

    # ------------------------------------------------------------------
    # Main update (called with dt in ms)
    # ------------------------------------------------------------------
    def update(self, dt: int, keys):
        if self.finished:
            return
        if self.paused:
            return

        self._clock_ms += dt
        all_entities = self._players + self._bots

        # --- Players ---
        for p in self._players:
            if not p.alive and p.state == DEAD and p._death_t <= 0:
                continue
            new_bomb = p.update(dt, keys, self._map, self._bombs)
            if new_bomb:
                self._bombs.append(new_bomb)
                self._play(self._snd_bomb)
            # Death sound trigger
            if not p.alive and p.state == DEAD and p._death_t == 800:
                self._play(self._snd_death)

        # --- Bots ---
        for bot in self._bots:
            if not bot.alive and bot.state == DEAD and bot._death_t <= 0:
                continue
            new_bomb = bot.update(dt, keys, self._map, self._bombs, self._players)
            if new_bomb:
                self._bombs.append(new_bomb)
                self._play(self._snd_bomb)
            # Death sound trigger
            if not bot.alive and bot.state == DEAD and bot._death_t == 800:
                self._play(self._snd_death)

        # --- Bombs ---
        new_explosions: list[Explosion] = []
        dead_bombs = []
        for b in self._bombs:
            exps = b.update(dt, self._map, all_entities, self._bombs)
            if exps:
                new_explosions.extend(exps)
                self._play(self._snd_exp)
            if not b.alive:
                dead_bombs.append(b)
        for b in dead_bombs:
            self._bombs.remove(b)
        self._explosions.extend(new_explosions)

        # --- Explosions ---
        dead_exp = []
        for e in self._explosions:
            e.update(dt)
            if not e.alive:
                dead_exp.append(e)
        for e in dead_exp:
            self._explosions.remove(e)

        # --- Power-ups ---
        dead_pu = []
        for pu in self._map.powerups:
            if not pu.alive:
                dead_pu.append(pu)
                continue
            for p in all_entities:
                if p.alive and p.get_rect().colliderect(pu.get_rect()):
                    p.apply_powerup(pu)
                    pu.alive = False
                    self._play(self._snd_pu)
                    p.score += 50
        for pu in dead_pu:
            if pu in self._map.powerups:
                self._map.powerups.remove(pu)

        # --- Win/loss check ---
        self._check_end()

    # ------------------------------------------------------------------
    # End condition
    # ------------------------------------------------------------------
    def _check_end(self):
        if self.mode == 'pvp':
            alive = [p for p in self._players if p.alive or p.state == RESPAWNING]
            if len(alive) <= 1:
                winner = alive[0] if alive else None
                winner_label = f"P{winner.player_id + 1}" if winner else "Empate!"
                self._finish(winner_label)

        elif self.mode == 'coop':
            alive_bots    = [b for b in self._bots   if b.alive or b.state == RESPAWNING]
            alive_players = [p for p in self._players if p.alive or p.state == RESPAWNING]
            if not alive_bots:
                self._finish("Jogadores")
            elif not alive_players:
                self._finish("Bots")

    def _finish(self, winner_label: str):
        if self.finished:
            return
        self.finished = True
        all_e = self._players + self._bots
        scores = [(f"P{e.player_id+1}" if not isinstance(e, Bot) else f"BOT{e.player_id-1}",
                   e.score) for e in all_e]
        self._result_data = (winner_label, scores)

    # ------------------------------------------------------------------
    # Pause toggle
    # ------------------------------------------------------------------
    def toggle_pause(self):
        self.paused = not self.paused

    def handle_pause_event(self, event) -> str | None:
        if self.paused:
            action = self._pause_menu.handle_event(event)
            if action == "Continuar":
                self.paused = False
            elif action in ("Sair para o Menu",):
                return action
        return None

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface):
        # Map + entities
        self._map.draw(surface)

        for b in self._bombs:
            b.draw(surface)
        for e in self._explosions:
            e.draw(surface)
        for p in self._players + self._bots:
            p.draw(surface)

        # HUD
        all_e = self._players + self._bots
        HUD(all_e).draw(surface)

        # Pause overlay
        if self.paused:
            self._pause_menu.draw(surface)

    # ------------------------------------------------------------------
    # Result screen
    # ------------------------------------------------------------------
    def get_result_screen(self):
        if self._result_data:
            return ResultScreen(*self._result_data)
        return None
