# ui.py
import pygame
import sys
import time
import random
import os
import math

from game import (
    ROW_COUNT, COLUMN_COUNT, J1, J2,
    crear_tablero, soltar_pieza, movimiento_valido,
    siguiente_fila_vacia, verificar_ganador, tablero_lleno
)
from ai_minimax import minimax, get_valid_locations
import td  # nuestro módulo td.py

# ------- CONFIG VISUAL -------
SQUARESIZE = 100
RADIUS = int(SQUARESIZE / 2 - 8)

AZUL = (25, 75, 255)
NEGRO = (20, 20, 20)
ROJO = (230, 60, 60)
AMARILLO = (250, 230, 40)
BLANCO = (240, 240, 240)
VERDE = (0, 255, 0)

# ------- PARÁMETROS (compatibilidad) -------
ALPHA = getattr(td, "ALPHA", 0.1)
GAMMA = getattr(td, "GAMMA", getattr(td, "GAMMA", 0.99))
EPSILON_HUMAN = 0.1
EPSILON_TRAIN = 0.2
MAX_DEPTH = 4
ERROR_PROB = 0.25

# Archivos de stats (usa td para compatibilidad)
STATS_FILE = getattr(td, "STATS_FILE", "td_stats.pkl")

# ------- ESTADO GLOBAL SIMPLE PARA UI -------
# Referencias a la tabla y episodios del módulo td
V = td.V           # referencia a la tabla V del módulo td
# No reasignamos episode_states aquí; siempre operamos sobre td.episode_states

# Stats en archivo (pequeña implementación)
def default_stats():
    return {
        "total_games": 0,
        1: {"games": 0, "td_wins": 0, "opp_wins": 0, "draws": 0},
        2: {"games": 0, "td_wins": 0, "opp_wins": 0, "draws": 0},
        3: {"games": 0, "td_wins": 0, "opp_wins": 0, "draws": 0},
    }

def cargar_stats():
    if os.path.exists(STATS_FILE):
        try:
            import pickle
            with open(STATS_FILE, "rb") as f:
                return pickle.load(f)
        except Exception:
            return default_stats()
    return default_stats()

def guardar_stats(s):
    import pickle
    with open(STATS_FILE, "wb") as f:
        pickle.dump(s, f)

def registrar_resultado_stats(stats, game_mode, player_roles, winner_mark):
    """Actualiza estadísticas globales persistentes (similar al original)."""
    if game_mode not in (1,2,3):
        return
    stats["total_games"] += 1
    m = stats[game_mode]
    m["games"] += 1

    if winner_mark is None:
        m["draws"] += 1
    else:
        role = player_roles.get(winner_mark)
        # comprobar si el ganador era el TD
        td_role_str = getattr(td, "ROLE_TD", "td")
        if role == "td" or role == td_role_str:
            m["td_wins"] += 1
        else:
            m["opp_wins"] += 1

    guardar_stats(stats)


# ------- DIBUJADO -------
def dibujar_tablero_pygame(screen, tablero, width, height):
    # Fondo azul del tablero y huecos negros
    for c in range(COLUMN_COUNT):
        for r in range(ROW_COUNT):
            pygame.draw.rect(screen, AZUL, (c*SQUARESIZE, (r+1)*SQUARESIZE, SQUARESIZE, SQUARESIZE))
            pygame.draw.circle(screen, NEGRO,
                (int(c*SQUARESIZE+SQUARESIZE/2), int((r+1)*SQUARESIZE+SQUARESIZE/2)),
                RADIUS)

    # Fichas
    for c in range(COLUMN_COUNT):
        for r in range(ROW_COUNT):
            if tablero[r][c] == J1:
                pygame.draw.circle(
                    screen, ROJO,
                    (int(c*SQUARESIZE+SQUARESIZE/2),
                     height-int(r*SQUARESIZE+SQUARESIZE/2)),
                    RADIUS
                )
            elif tablero[r][c] == J2:
                pygame.draw.circle(
                    screen, AMARILLO,
                    (int(c*SQUARESIZE+SQUARESIZE/2),
                     height-int(r*SQUARESIZE+SQUARESIZE/2)),
                    RADIUS
                )

    pygame.display.update()


def animar_caida(screen, tablero, col, fila_final, color, width, height):
    for f in range(ROW_COUNT):
        if f > fila_final:
            break
        dibujar_tablero_pygame(screen, tablero, width, height)
        pygame.draw.circle(screen, color,
            (int(col*SQUARESIZE+SQUARESIZE/2),
             int(SQUARESIZE/2 + (f+1)*SQUARESIZE)),
            RADIUS)
        pygame.display.update()
        time.sleep(0.04)


def dibujar_linea_ganadora(screen, lista, width, height):
    for (r, c) in lista:
        pygame.draw.circle(
            screen, VERDE,
            (int(c*SQUARESIZE + SQUARESIZE/2),
             height - int(r*SQUARESIZE + SQUARESIZE/2)),
            RADIUS
        )


# ------- MAIN UI / LOOP -------
def main():
    global width, height

    # Inicializar pygame
    pygame.init()
    width = COLUMN_COUNT * SQUARESIZE + 400
    height = (ROW_COUNT + 1) * SQUARESIZE
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Conecta 4 - TD Learning")

    fuente = pygame.font.SysFont("arial", 45, bold=True)
    fuente_small = pygame.font.SysFont("arial", 22, bold=False)

    # Cargar TD y stats
    td.cargar_valores()
    stats = cargar_stats()

    # Estado inicial
    state = "menu"
    tablero = crear_tablero()
    turno = J1
    posiciones_ganadoras = None
    game_over = False
    columna_actual = COLUMN_COUNT // 2

    # roles y modos
    ROLE_HUMANO = "human"
    ROLE_TD = "td"
    ROLE_MINIMAX_PERF = "minimax_perfect"
    ROLE_MINIMAX_SEMI = "minimax_semi"

    role_labels = {
        ROLE_HUMANO: "Humano",
        ROLE_TD: "Aprendiz",
        ROLE_MINIMAX_PERF: "IA Perfecta",
        ROLE_MINIMAX_SEMI: "IA Semiperfecta"
    }
    mode_labels = {
        1: "Aprendiz vs Humano",
        2: "Aprendiz vs IA Perfecta",
        3: "Aprendiz vs IA Semiperfecta"
    }

    # variables que controlan el modo seleccionado
    game_mode = None
    apprentice_mark = None
    player_roles = {}
    auto_restart = False

    # Contadores visuales
    num_games = 0
    victorias_j1 = 0
    victorias_j2 = 0

    # info debug
    ultimo_mov_td = "-"
    valor_estado_actual = 0.0
    epsilon_actual = 0.0

    clock = pygame.time.Clock()

    def configurar_modo(modo):
        nonlocal game_mode, player_roles, apprentice_mark, auto_restart, num_games
        game_mode = modo
        num_games = 0
        if modo == 1:
            player_roles = {J1: ROLE_HUMANO, J2: ROLE_TD}
            apprentice_mark = J2
            auto_restart = False
        elif modo == 2:
            player_roles = {J1: ROLE_TD, J2: ROLE_MINIMAX_PERF}
            apprentice_mark = J1
            auto_restart = True
        elif modo == 3:
            player_roles = {J1: ROLE_TD, J2: ROLE_MINIMAX_SEMI}
            apprentice_mark = J1
            auto_restart = True

    def nueva_partida():
        # no usamos 'nonlocal' para td.episode_states (es del módulo td)
        nonlocal tablero, turno, posiciones_ganadoras, game_over, ultimo_mov_td, valor_estado_actual, epsilon_actual, num_games
        # limpiar la lista del módulo td (episodio anterior)
        td.episode_states.clear()
        tablero, turno = generar_tablero_partida_real()
        posiciones_ganadoras = None
        game_over = False
        ultimo_mov_td = "-"
        valor_estado_actual = 0.0
        epsilon_actual = 0.0
        dibujar_tablero_pygame(screen, tablero, width, height)

    # Re-implementamos la función generar_tablero_partida_real localmente
    # (para evitar dependencias extras)
    def generar_tablero_partida_real():
        while True:
            t = crear_tablero()
            jugadas_previas = random.randint(0, ROW_COUNT * COLUMN_COUNT - 12)
            jugador = random.choice([J1, J2])
            turnos = []
            for _ in range(jugadas_previas):
                turnos.append(jugador)
                jugador = J2 if jugador == J1 else J1

            for pieza in turnos:
                columnas_validas = [c for c in range(COLUMN_COUNT) if movimiento_valido(t, c)]
                if not columnas_validas:
                    break
                col = random.choice(columnas_validas)
                fila = siguiente_fila_vacia(t, col)
                soltar_pieza(t, fila, col, pieza)

                if verificar_ganador(t, J1) or verificar_ganador(t, J2):
                    break
            else:
                if len(turnos) == 0:
                    siguiente = random.choice([J1, J2])
                else:
                    ultimo = turnos[-1]
                    siguiente = J2 if ultimo == J1 else J1
                return t, siguiente

    # Inicia en menú
    dibujar_tablero_pygame(screen, tablero, width, height)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                td.guardar_valores()
                pygame.quit()
                sys.exit()

            if state == "menu":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1:
                        configurar_modo(1)
                        nueva_partida()
                        state = "game"
                    elif event.key == pygame.K_2:
                        configurar_modo(2)
                        nueva_partida()
                        state = "game"
                    elif event.key == pygame.K_3:
                        configurar_modo(3)
                        nueva_partida()
                        state = "game"
                    elif event.key == pygame.K_ESCAPE:
                        td.guardar_valores()
                        pygame.quit()
                        sys.exit()

            elif state == "game":
                # Movimiento del humano (si le toca)
                if event.type == pygame.KEYDOWN and not game_over and player_roles.get(turno) == ROLE_HUMANO:
                    if event.key == pygame.K_LEFT:
                        columna_actual = max(0, columna_actual - 1)
                    elif event.key == pygame.K_RIGHT:
                        columna_actual = min(COLUMN_COUNT - 1, columna_actual + 1)
                    elif event.key == pygame.K_SPACE:
                        if movimiento_valido(tablero, columna_actual):
                            fila = siguiente_fila_vacia(tablero, columna_actual)
                            animar_caida(screen, tablero, columna_actual, fila, ROJO, width, height)
                            soltar_pieza(tablero, fila, columna_actual, J1)

                            gan = verificar_ganador(tablero, J1)
                            if gan:
                                posiciones_ganadoras = gan
                                game_over = True
                                ultimo_ganador = J1
                                num_games += 1
                            elif tablero_lleno(tablero):
                                game_over = True
                                ultimo_ganador = None
                                num_games += 1
                            else:
                                turno = J2

                            dibujar_tablero_pygame(screen, tablero, width, height)
                            if game_over and not auto_restart:
                                continue

                # Reinicio en modo humano (espacio)
                if event.type == pygame.KEYDOWN and game_mode == 1 and game_over:
                    if event.key == pygame.K_SPACE:
                        nueva_partida()

        # Lógica fuera de eventos
        if state == "menu":
            # dibujar menú
            screen.fill(NEGRO)
            titulo = fuente.render("Conecta 4 - Menú Principal", True, BLANCO)
            screen.blit(titulo, (width//2 - titulo.get_width()//2, 60))
            opciones = [
                "1) IA Aprendiz vs Humano",
                "2) IA Aprendiz vs IA Perfecta (Minimax)",
                "3) IA Aprendiz vs IA Semiperfecta (Minimax Aleatoria)",
                "ESC) Salir"
            ]
            for i, txt in enumerate(opciones):
                surf = fuente_small.render(txt, True, BLANCO)
                screen.blit(surf, (80, 160 + i*40))

            # stats
            y0 = 160
            x_stats = width//2 + 40
            screen.blit(fuente_small.render("Estadísticas globales:", True, BLANCO), (x_stats, y0-30))
            screen.blit(fuente_small.render(f"Total partidas: {stats['total_games']}", True, BLANCO), (x_stats, y0))
            for modo in (1,2,3):
                m = stats[modo]
                txt = f"Modo {modo} - Partidas: {m['games']} | TD gana: {m['td_wins']} | Rival: {m['opp_wins']} | Emp: {m['draws']}"
                screen.blit(fuente_small.render(txt, True, BLANCO), (x_stats, y0 + 30*modo))

            pygame.display.update()
            clock.tick(10)
            continue

        # Si estamos en juego:
        if state == "game":
            # Turno IA Aprendiz (TD)
            if not game_over and player_roles.get(turno) == ROLE_TD:
                pygame.time.wait(120)
                # Registrar estado actual para TD
                td.registrar_estado(tablero, apprentice_mark)

                # elegir epsilon según modo
                td.EPSILON = EPSILON_TRAIN if game_mode in (2, 3) else EPSILON_HUMAN
                col, tipo = td.td_elegir_movimiento(tablero, apprentice_mark)

                if col is not None and movimiento_valido(tablero, col):
                    fila = siguiente_fila_vacia(tablero, col)
                    color = ROJO if apprentice_mark == J1 else AMARILLO
                    animar_caida(screen, tablero, col, fila, color, width, height)
                    soltar_pieza(tablero, fila, col, apprentice_mark)

                    # Depuración
                    ultimo_mov_td = tipo
                    epsilon_actual = td.EPSILON
                    key2 = td.get_state_key(tablero, apprentice_mark)
                    valor_estado_actual = td.V.get(key2, 0.0)
                    td.registrar_estado(tablero, apprentice_mark)

                    gan = verificar_ganador(tablero, apprentice_mark)
                    if gan:
                        posiciones_ganadoras = gan
                        game_over = True
                        ultimo_ganador = apprentice_mark
                    elif tablero_lleno(tablero):
                        game_over = True
                        ultimo_ganador = None
                    else:
                        turno = J1 if apprentice_mark == J2 else J2

                    dibujar_tablero_pygame(screen, tablero, width, height)

            # Turno IA Minimax (perfecta o semiperfecta)
            if not game_over and player_roles.get(turno) in (ROLE_MINIMAX_PERF, ROLE_MINIMAX_SEMI):
                pygame.time.wait(120)
                pieza_max = turno
                valid_moves = get_valid_locations(tablero)

                if player_roles[turno] == ROLE_MINIMAX_SEMI and random.random() < ERROR_PROB:
                    col = random.choice(valid_moves)
                else:
                    col, _ = minimax(tablero, MAX_DEPTH, -math.inf, math.inf, True, pieza_max)

                if movimiento_valido(tablero, col):
                    fila = siguiente_fila_vacia(tablero, col)
                    color = ROJO if turno == J1 else AMARILLO
                    animar_caida(screen, tablero, col, fila, color, width, height)
                    soltar_pieza(tablero, fila, col, turno)

                    gan = verificar_ganador(tablero, turno)
                    if gan:
                        posiciones_ganadoras = gan
                        game_over = True
                        ultimo_ganador = turno
                    elif tablero_lleno(tablero):
                        game_over = True
                        ultimo_ganador = None
                    else:
                        turno = J1 if turno == J2 else J2

                    dibujar_tablero_pygame(screen, tablero, width, height)

            # HUD superior + panel derecho
            pygame.draw.rect(screen, NEGRO, (0, 0, width, SQUARESIZE))

            if game_over:
                if ultimo_ganador is None:
                    color_txt = BLANCO
                else:
                    color_txt = ROJO if ultimo_ganador == J1 else AMARILLO
                winner_text = "Empate" if ultimo_ganador is None else (
                    "Humano" if ultimo_ganador == J1 and player_roles.get(J1) == ROLE_HUMANO else "IA"
                )
                text_g = fuente.render(("Empate" if ultimo_ganador is None else f"Gana {winner_text}"), True, color_txt)
                screen.blit(text_g, (10, 5))

                if not auto_restart and game_mode == 1:
                    text_r = fuente_small.render("Presiona ESPACIO para siguiente partida", True, BLANCO)
                    screen.blit(text_r, (10, 50))

            # Panel derecho (simple)
            panel_rect = (COLUMN_COUNT*SQUARESIZE, 0, width-COLUMN_COUNT*SQUARESIZE, height)
            pygame.draw.rect(screen, (40,40,40), panel_rect)

            px = COLUMN_COUNT * SQUARESIZE + 20
            m = stats.get(game_mode, {"games":0,"td_wins":0,"opp_wins":0,"draws":0})
            total_modo = max(1, m["games"])
            winrate = 100.0 * m["td_wins"] / total_modo

            screen.blit(fuente_small.render(f"Modo: {mode_labels.get(game_mode,'')}", True, BLANCO), (px, 10))
            screen.blit(fuente_small.render(f"Partida sesión: {num_games}", True, BLANCO), (px, 40))
            screen.blit(fuente_small.render(f"Partidas totales (modo): {m['games']}", True, BLANCO), (px, 70))
            screen.blit(fuente_small.render(f"TD gana: {m['td_wins']} | Rival: {m['opp_wins']} | Emp: {m['draws']}", True, BLANCO), (px, 100))

            screen.blit(fuente_small.render(f"Estados aprendidos: {len(td.V)}", True, BLANCO), (px, 170))
            screen.blit(fuente_small.render(f"Último mov TD: {ultimo_mov_td}", True, BLANCO), (px, 200))
            screen.blit(fuente_small.render(f"Valor V(s): {valor_estado_actual:.3f}", True, BLANCO), (px, 230))
            screen.blit(fuente_small.render(f"Epsilon: {epsilon_actual:.2f}", True, BLANCO), (px, 260))

            # ficha fantasma para humano
            if not game_over and player_roles.get(turno) == ROLE_HUMANO:
                pygame.draw.circle(screen, ROJO,
                    (int(columna_actual*SQUARESIZE+SQUARESIZE/2), int(SQUARESIZE/2)), RADIUS)

            if posiciones_ganadoras:
                dibujar_linea_ganadora(screen, posiciones_ganadoras, width, height)

            pygame.display.update()

            # auto reinicio en modos IA vs IA
            if game_over and auto_restart:
                # actualizar TD si corresponde
                if apprentice_mark is not None:
                    resultado = td.obtener_recompensa(tablero, apprentice_mark)
                    td.actualizar_td(resultado)
                    registrar_resultado_stats(stats, game_mode, player_roles, ultimo_ganador)
                pygame.time.wait(150)
                nueva_partida()

        clock.tick(60)


if __name__ == "__main__":
    main()
