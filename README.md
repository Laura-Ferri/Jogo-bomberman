# BomberPy — SNES Edition

Clone do clássico **Bomberman** em Python + Pygame com estética pixel art 16 bits SNES.

## Requisitos

- Python 3.10+ (testado em 3.14)
- `pygame-ce` (Community Edition)

```bash
py -m pip install pygame-ce
```

## Como Jogar

```bash
py main.py
```
Ou clique duas vezes em **`jogar.bat`**

---

## Controles

| Ação | Jogador 1 | Jogador 2 |
|------|-----------|-----------|
| Mover | `W A S D` | `↑ ↓ ← →` |
| Bomba | `Espaço` | `Enter` |
| Pausar | `ESC` | `ESC` |

---

## Modos de Jogo

| Modo | Descrição |
|------|-----------|
| **PvP Mata-Mata** | 1 ou 2 jogadores humanos |
| **Cooperativo** | 2 jogadores vs 2 bots IA |

## Dificuldade dos Bots

| Nível | Intervalo de Decisão | Fuga da Explosão |
|-------|---------------------|-----------------|
| Fácil | 1.5s | 2.0s de margem |
| Médio | 0.8s | 1.2s de margem |
| Difícil | 0.28s | 0.6s de margem |

---

## Power-ups

| Ícone | Tipo | Efeito |
|-------|------|--------|
| 🔥 Cruz laranja | Alcance | +1 tile de explosão |
| ⚡ Raio azul | Velocidade | +0.8 px/frame |
| 💣 Bomba verde | Extra Bomba | +1 bomba simultânea |

---

## Estrutura do Projeto

```
Jogo/
├── main.py        ← Entrada + máquina de estados de telas
├── game.py        ← Coordenador: update/draw/lógica
├── map.py         ← Grid 15×13, geração, colisão
├── player.py      ← Jogador humano (FSM + movimento)
├── enemy.py       ← Bot IA (FSM: FLEE/BOMB/HUNT/WANDER + BFS)
├── bomb.py        ← Bomba + explosão em cruz + chain reaction
├── powerup.py     ← Power-ups (range/speed/extra_bomb)
├── hud.py         ← HUD: vidas, score, bombas, alcance
├── menu.py        ← Todas as telas de menu
├── settings.py    ← Constantes globais e paleta SNES
├── jogar.bat      ← Atalho para iniciar no Windows
└── assets/
    ├── sprites/   ← (opcional) PNGs de sprites
    ├── sounds/    ← (opcional) .ogg SFX
    └── music/     ← (opcional) .ogg BGM
```

> **Nota**: O jogo funciona sem nenhum arquivo em `assets/` — todos os gráficos são renderizados programaticamente via `pygame.draw`.
