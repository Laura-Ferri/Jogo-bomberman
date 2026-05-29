"""
BomberPy — SNES Edition
Entry point: manages the top-level screen stack (Menu → Game → Result).
"""
import sys
import pygame
from settings import (
    TITLE, WINDOW_W, WINDOW_H, FPS, DEFAULT_VOLUME,
    PLAYER_COLORS, C_BG
)
from menu import MainMenu, ModeSelect, PlayerSelect, OptionsMenu, ResultScreen
from game import Game


def main():
    pygame.init()
    pygame.mixer.init()
    pygame.display.set_caption(TITLE)

    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    clock  = pygame.time.Clock()

    # Shared state
    volume     = DEFAULT_VOLUME
    difficulty = 'medium'

    # Screen stack states
    STATE_MAIN    = 'main'
    STATE_MODE    = 'mode'
    STATE_PLAYERS = 'players'
    STATE_OPTIONS = 'options'
    STATE_GAME    = 'game'
    STATE_RESULT  = 'result'

    state      = STATE_MAIN
    mode       = 'pvp'
    num_players = 1
    colors     = [PLAYER_COLORS[0], PLAYER_COLORS[1]]

    # Screen instances (re-created as needed)
    main_menu     = MainMenu()
    mode_select   = ModeSelect()
    player_select = PlayerSelect(num_players)
    options_menu  = OptionsMenu(volume, difficulty)
    game_inst: Game | None = None
    result_screen: ResultScreen | None = None

    while True:
        dt = clock.tick(FPS)

        # ── Events ──────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # ESC pauses if in game
            if state == STATE_GAME and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if game_inst:
                        game_inst.toggle_pause()

            if state == STATE_MAIN:
                action = main_menu.handle_event(event)
                if action == "Iniciar Jogo":
                    mode_select = ModeSelect()
                    state       = STATE_MODE
                elif action == "Opções":
                    options_menu = OptionsMenu(volume, difficulty)
                    state        = STATE_OPTIONS
                elif action == "Sair":
                    pygame.quit()
                    sys.exit()

            elif state == STATE_MODE:
                action = mode_select.handle_event(event)
                if action == "PvP Mata-Mata":
                    mode          = 'pvp'
                    player_select = PlayerSelect(2, 'pvp')
                    state         = STATE_PLAYERS
                elif action == "1v1 (Player vs PC)":
                    mode          = '1v1'
                    player_select = PlayerSelect(1, '1v1')
                    state         = STATE_PLAYERS
                elif action == "Cooperativo (2J vs 2 Bots)":
                    # Apenas cor do time importa; game.py aplica em P1 e P2
                    mode          = 'coop'
                    player_select = PlayerSelect(1, 'coop')
                    state         = STATE_PLAYERS
                elif action == "Voltar":
                    state         = STATE_MAIN

            elif state == STATE_PLAYERS:
                cfg = player_select.handle_event(event)
                if cfg:
                    if cfg.get('back'):
                        state = STATE_MODE
                    else:
                        num_players = cfg['num_players']
                        colors      = cfg['colors']
                        game_inst   = Game(mode, colors, difficulty, volume)
                        state       = STATE_GAME

            elif state == STATE_OPTIONS:
                action = options_menu.handle_event(event)
                if action == 'back':
                    volume     = options_menu.volume
                    difficulty = options_menu.difficulty
                    state      = STATE_MAIN

            elif state == STATE_GAME:
                if game_inst:
                    action = game_inst.handle_pause_event(event)
                    if action == "Sair para o Menu":
                        state = STATE_MAIN

            elif state == STATE_RESULT:
                if result_screen:
                    action = result_screen.handle_event(event)
                    if action == 'menu':
                        state = STATE_MAIN

        # ── Update ──────────────────────────────────────────────────────
        keys = pygame.key.get_pressed()

        if state == STATE_MAIN:
            main_menu.update(dt)
        elif state == STATE_MODE:
            mode_select.update(dt)
        elif state == STATE_PLAYERS:
            player_select.update(dt)
        elif state == STATE_OPTIONS:
            options_menu.update(dt)
        elif state == STATE_GAME:
            if game_inst:
                game_inst.update(dt, keys)
                if game_inst.finished:
                    result_screen = game_inst.get_result_screen()
                    state = STATE_RESULT
        elif state == STATE_RESULT:
            if result_screen:
                result_screen.update(dt)

        # ── Draw ────────────────────────────────────────────────────────
        screen.fill(C_BG)

        if state == STATE_MAIN:
            main_menu.draw(screen)
        elif state == STATE_MODE:
            mode_select.draw(screen)
        elif state == STATE_PLAYERS:
            player_select.draw(screen)
        elif state == STATE_OPTIONS:
            options_menu.draw(screen)
        elif state == STATE_GAME:
            if game_inst:
                game_inst.draw(screen)
        elif state == STATE_RESULT:
            if result_screen:
                result_screen.draw(screen)

        pygame.display.flip()


if __name__ == '__main__':
    main()
