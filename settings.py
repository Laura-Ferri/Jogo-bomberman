# pyrefly: ignore [missing-import]
import pygame

# --- Display ---
TILE_SIZE = 48
GRID_W    = 15
GRID_H    = 13
HUD_H     = 96
SCREEN_W  = TILE_SIZE * GRID_W   # 720
SCREEN_H  = TILE_SIZE * GRID_H   # 624
WINDOW_W  = SCREEN_W
WINDOW_H  = SCREEN_H + HUD_H     # 720
FPS       = 60
TITLE     = "BomberPy — SNES Edition"

# --- Tile Types ---
EMPTY      = 0
WALL_SOLID = 1
WALL_SOFT  = 2

# --- SNES Palette (no purple) ---
C_BG           = ( 20,  28,  40)
C_FLOOR        = ( 44,  58,  72)
C_FLOOR_ALT    = ( 38,  50,  65)
C_WALL_SOLID   = ( 28,  36,  52)
C_WALL_SOLID_H = ( 42,  54,  78)
C_WALL_SOFT    = (140,  90,  40)
C_WALL_SOFT_H  = (180, 120,  60)
C_WALL_SOFT_D  = (100,  62,  22)
C_EXPLOSION_C  = (255, 240,  60)
C_EXPLOSION_M  = (255, 160,  20)
C_EXPLOSION_O  = (255,  80,  20)
C_BOMB         = ( 22,  22,  22)
C_BOMB_GLOW    = (255, 100,   0)
C_HUD_BG       = ( 12,  16,  26)
C_HUD_LINE     = ( 30,  40,  60)
C_HUD_TEXT     = (240, 220, 160)
C_HUD_ACCENT   = (255, 160,  40)
C_WHITE        = (255, 255, 255)
C_BLACK        = (  0,   0,   0)
C_POWERUP_R    = (255, 120,  40)
C_POWERUP_S    = ( 60, 200, 255)
C_POWERUP_B    = ( 60, 220, 100)

# --- Player Colors ---
PLAYER_COLORS = [
    (240, 180,  60),  # P1: amber
    ( 60, 180, 240),  # P2: sky blue
    ( 60, 220, 120),  # Bot1: mint
    (220,  80,  60),  # Bot2: coral
]

# --- Controls ---
CONTROLS = {
    0: {
        'up':    pygame.K_w,
        'down':  pygame.K_s,
        'left':  pygame.K_a,
        'right': pygame.K_d,
        'bomb':  pygame.K_SPACE,
    },
    1: {
        'up':    pygame.K_UP,
        'down':  pygame.K_DOWN,
        'left':  pygame.K_LEFT,
        'right': pygame.K_RIGHT,
        'bomb':  pygame.K_RALT,
    },
}

# --- Difficulty ---
DIFFICULTY = {
    'easy':   {'interval': 1500, 'flee_margin': 2000},
    'medium': {'interval': 800,  'flee_margin': 1200},
    'hard':   {'interval': 280,  'flee_margin': 600},
}

# --- Timing ---
BOMB_FUSE_MS   = 3000
EXPLOSION_MS   = 600
RESPAWN_MS     = 2000

# --- Gameplay ---
POWERUP_CHANCE = 0.40
DEFAULT_VOLUME = 0.7
PLAYER_SPEED   = 3.0    # px/frame
PLAYER_LIVES   = 3
PLAYER_BOMBS   = 1
PLAYER_RANGE   = 2
HITBOX_SHRINK  = 6      # pixels inset on each side for collision box
