#ui.py
#interfaz gráfica del juego Conecta 4 con pygame, control de modos, animaciones,
#interacción humano/ia y conexión con las IAs (TD y Minimax)

import pygame
import sys
import time
import random
import os
import math

#funciones principales del juego base
from game import (
    ROW_COUNT, COLUMN_COUNT, J1, J2,
    crear_tablero, soltar_pieza, movimiento_valido,
    siguiente_fila_vacia, verificar_ganador, tablero_lleno
)

from ai_minimax import minimax, get_valid_locations
import td  #módulo de aprendizaje TD


#configuración visual
SQUARESIZE = 100
RADIUS = int(SQUARESIZE / 2 - 8)

AZUL = (25, 75, 255)
NEGRO = (20, 20, 20)
ROJO = (230, 60, 60)
AMARILLO = (250, 230, 40)
BLANCO = (240, 240, 240)
VERDE = (0, 255, 0)

#parámetros lógicos usados por la ui y td
ALPHA = getattr(td, "ALPHA", 0.1)
GAMMA = getattr(td, "GAMMA", 0.99)
EPSILON_HUMAN = 0.1      #epsilon más bajo cuando se juega contra humano
EPSILON_TRAIN = 0.2      #epsilon más alto durante entrenamiento IA vs IA
MAX_DEPTH = 4            #profundidad de minimax
ERROR_PROB = 0.25        #probabilidad de error de la IA semiperfecta

STATS_FILE = getattr(td, "STATS_FILE", "td_stats.pkl")

#referencia directa a la tabla de valores del TD
V = td.V


#manejo de estadísticas persistentes
def default_stats():
    #estructura base del archivo de estadísticas
    return {
        "total_games": 0,
        1: {"games": 0, "td_wins": 0, "opp_wins": 0, "draws": 0},
        2: {"games": 0, "td_wins": 0, "opp_wins": 0, "draws": 0},
        3: {"games": 0, "td_wins": 0, "opp_wins": 0, "draws": 0},
    }

def cargar_stats():
    #carga las estadísticas si existen, si no, devuelve estructura vacía
    if os.path.exists(STATS_FILE):
        try:
            import pickle
            with open(STATS_FILE, "rb") as f:
                return pickle.load(f)
        except:
            return default_stats()
    return default_stats()

def guardar_stats(s):
    #guarda las estadísticas en disco
    import pickle
    with open(STATS_FILE, "wb") as f:
        pickle.dump(s, f)

def registrar_resultado_stats(stats, game_mode, player_roles, winner_mark):
    #actualiza la tabla de estadísticas según el ganador
    if game_mode not in (1,2,3):
        return

    stats["total_games"] += 1
    m = stats[game_mode]
    m["games"] += 1

    #empate
    if winner_mark is None:
        m["draws"] += 1
    else:
        #identificar si quien ganó es el aprendiz
        role = player_roles.get(winner_mark)
        td_role_name = getattr(td, "ROLE_TD", "td")

        if role == "td" or role == td_role_name:
            m["td_wins"] += 1
        else:
            m["opp_wins"] += 1

    guardar_stats(stats)

#dibujado del tablero y animaciones
def dibujar_tablero_pygame(screen, tablero, width, height):
    #fondo azul con huecos negros
    for c in range(COLUMN_COUNT):
        for r in range(ROW_COUNT):
            pygame.draw.rect(screen, AZUL, (c*SQUARESIZE, (r+1)*SQUARESIZE, SQUARESIZE, SQUARESIZE))
            pygame.draw.circle(screen, NEGRO,
                (int(c*SQUARESIZE+SQUARESIZE/2), int((r+1)*SQUARESIZE+SQUARESIZE/2)),
                RADIUS)

    #fichas de ambos jugadores
    for c in range(COLUMN_COUNT):
        for r in range(ROW_COUNT):
            if tablero[r][c] == J1:
                pygame.draw.circle(screen, ROJO,
                    (int(c*SQUARESIZE+SQUARESIZE/2),
                     height-int(r*SQUARESIZE+SQUARESIZE/2)),
                    RADIUS)
            elif tablero[r][c] == J2:
                pygame.draw.circle(screen, AMARILLO,
                    (int(c*SQUARESIZE+SQUARESIZE/2),
                     height-int(r*SQUARESIZE+SQUARESIZE/2)),
                    RADIUS)

    pygame.display.update()

def animar_caida(screen, tablero, col, fila_final, color, width, height):
    #animación: la ficha cae cuadro por cuadro visualmente
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
    #marca las cuatro fichas ganadoras en verde
    for (r, c) in lista:
        pygame.draw.circle(
            screen, VERDE,
            (int(c*SQUARESIZE + SQUARESIZE/2),
             height - int(r*SQUARESIZE + SQUARESIZE/2)),
            RADIUS
        )

#main loop de la interfaz
def main():
    global width, height

    pygame.init()

    #tamaño total de ventana (tablero + panel derecho)
    width = COLUMN_COUNT * SQUARESIZE + 400
    height = (ROW_COUNT + 1) * SQUARESIZE
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Conecta 4 - TD Learning")

    #fuentes del texto
    fuente = pygame.font.SysFont("arial", 45, bold=True)
    fuente_small = pygame.font.SysFont("arial", 22, bold=False)

    #cargar valores aprendidos y estadísticas
    td.cargar_valores()
    stats = cargar_stats()

    #estado inicial
    state = "menu"
    tablero = crear_tablero()
    turno = J1
    posiciones_ganadoras = None
    game_over = False
    columna_actual = COLUMN_COUNT // 2

    #roles jugables disponibles
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

    #variables de configuración del modo
    game_mode = None
    apprentice_mark = None
    player_roles = {}
    auto_restart = False

    #contadores de la sesión actual
    num_games = 0

    #info de depuración del TD
    ultimo_mov_td = "-"
    valor_estado_actual = 0.0
    epsilon_actual = 0.0

    clock = pygame.time.Clock()

    #función: configurar el modo jugable actual
    def configurar_modo(modo):
        nonlocal game_mode, player_roles, apprentice_mark, auto_restart, num_games
        game_mode = modo
        num_games = 0
        #humano vs aprendiz
        if modo == 1:        
            player_roles = {J1: ROLE_HUMANO, J2: ROLE_TD}
            apprentice_mark = J2
            auto_restart = False
        #aprendiz vs ia perfecta
        elif modo == 2:      
            player_roles = {J1: ROLE_TD, J2: ROLE_MINIMAX_PERF}
            apprentice_mark = J1
            auto_restart = True
        #aprendiz vs ia semiperfecta
        elif modo == 3:      
            player_roles = {J1: ROLE_TD, J2: ROLE_MINIMAX_SEMI}
            apprentice_mark = J1
            auto_restart = True

    #iniciar una partida nueva
    def nueva_partida():
        nonlocal tablero, turno, posiciones_ganadoras, game_over
        nonlocal ultimo_mov_td, valor_estado_actual, epsilon_actual, num_games
        #limpiar los estados vistos anteriormente
        td.episode_states.clear()   

        tablero, turno = generar_tablero_partida_real()
        posiciones_ganadoras = None
        game_over = False
        ultimo_mov_td = "-"
        valor_estado_actual = 0.0
        epsilon_actual = 0.0

        dibujar_tablero_pygame(screen, tablero, width, height)

    #generación de posiciones aleatorias para entrenamiento
    def generar_tablero_partida_real():
        #genera un estado intermedio aleatorio evitando estados ya ganados
        #esto aumenta la variedad de situaciones desde las que el TD aprende
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
                #si no hubo ganador, el turno siguiente es coherente
                siguiente = random.choice([J1, J2]) if len(turnos)==0 else (J2 if turnos[-1]==J1 else J1)
                return t, siguiente

    #dibujo inicial del tablero
    dibujar_tablero_pygame(screen, tablero, width, height)

    #main loop
    while True:
        #eventos (teclado, mouse, cerrar ventana)
        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                td.guardar_valores()
                pygame.quit()
                sys.exit()

            #menú principal
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

            #interacción humana en la partida
            elif state == "game":
                #movimiento del jugador humano
                if event.type == pygame.KEYDOWN and not game_over and player_roles.get(turno)==ROLE_HUMANO:
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

                #reinicio cuando humano está jugando
                if event.type == pygame.KEYDOWN and game_mode==1 and game_over:
                    if event.key == pygame.K_SPACE:
                        nueva_partida()

        #lógica de menú
        if state == "menu":
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

            #mostrar estadísticas globales
            y0 = 160
            x_stats = width//2 + 40
            screen.blit(fuente_small.render("Estadísticas globales:", True, BLANCO), (x_stats, y0-30))
            screen.blit(fuente_small.render(f"Total partidas: {stats['total_games']}", True, BLANCO), (x_stats, y0))

            for modo in (1,2,3):
                m = stats[modo]
                txt = f"Modo {modo} - Partidas: {m['games']} | TD gana: {m['td_wins']} | Rival: {m['opp_wins']} | Emp: {m['draws']}"
                screen.blit(fuente_small.render(txt, True, BLANCO), (x_stats, y0+30*modo))

            pygame.display.update()
            clock.tick(10)
            continue

        #juego activo
        if state == "game":

            #turno del TD (aprendiz)
            if not game_over and player_roles.get(turno)==ROLE_TD:
                pygame.time.wait(120)

                td.registrar_estado(tablero, apprentice_mark)

                #ajustar epsilon según modo
                td.EPSILON = EPSILON_TRAIN if game_mode in (2,3) else EPSILON_HUMAN

                col, tipo = td.td_elegir_movimiento(tablero, apprentice_mark)

                if col is not None and movimiento_valido(tablero, col):
                    fila = siguiente_fila_vacia(tablero, col)
                    color = ROJO if apprentice_mark==J1 else AMARILLO

                    animar_caida(screen, tablero, col, fila, color, width, height)
                    soltar_pieza(tablero, fila, col, apprentice_mark)

                    ultimo_mov_td = tipo
                    epsilon_actual = td.EPSILON
                    key_state = td.get_state_key(tablero, apprentice_mark)
                    valor_estado_actual = td.V.get(key_state, 0.0)

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
                        turno = J1 if apprentice_mark==J2 else J2

                    dibujar_tablero_pygame(screen, tablero, width, height)

            #turno de IA Minimax (perfecta o semiperfecta)
            if not game_over and player_roles.get(turno) in (ROLE_MINIMAX_PERF, ROLE_MINIMAX_SEMI):
                pygame.time.wait(120)
                pieza_max = turno
                valid_moves = get_valid_locations(tablero)

                #ia semiperfecta tiene errores intencionales
                if player_roles[turno]==ROLE_MINIMAX_SEMI and random.random() < ERROR_PROB:
                    col = random.choice(valid_moves)
                else:
                    col, _ = minimax(tablero, MAX_DEPTH, -math.inf, math.inf, True, pieza_max)

                if movimiento_valido(tablero, col):
                    fila = siguiente_fila_vacia(tablero, col)
                    color = ROJO if turno==J1 else AMARILLO
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
                        turno = J1 if turno==J2 else J2

                    dibujar_tablero_pygame(screen, tablero, width, height)

            #hud superior y panel lateral informativo
            pygame.draw.rect(screen, NEGRO, (0,0,width,SQUARESIZE))

            if game_over:
                color_txt = BLANCO if ultimo_ganador is None else (ROJO if ultimo_ganador==J1 else AMARILLO)
                winner_text = "Empate" if ultimo_ganador is None else (
                    "Humano" if ultimo_ganador==J1 and player_roles.get(J1)==ROLE_HUMANO else "IA"
                )
                text_g = fuente.render(("Empate" if ultimo_ganador is None else f"Gana {winner_text}"), True, color_txt)
                screen.blit(text_g, (10,5))

                if not auto_restart and game_mode==1:
                    text_r = fuente_small.render("Presiona ESPACIO para siguiente partida", True, BLANCO)
                    screen.blit(text_r, (10,50))

            #panel lateral a la derecha
            pygame.draw.rect(screen, (40,40,40),
                             (COLUMN_COUNT*SQUARESIZE, 0, width-COLUMN_COUNT*SQUARESIZE, height))

            px = COLUMN_COUNT * SQUARESIZE + 20
            m = stats.get(game_mode, {"games":0,"td_wins":0,"opp_wins":0,"draws":0})

            screen.blit(fuente_small.render(f"Modo: {mode_labels.get(game_mode,'')}", True, BLANCO), (px,10))
            screen.blit(fuente_small.render(f"Partida sesión: {num_games}", True, BLANCO), (px,40))
            screen.blit(fuente_small.render(f"Partidas totales (modo): {m['games']}", True, BLANCO), (px,70))
            screen.blit(fuente_small.render(f"TD gana: {m['td_wins']} | Rival: {m['opp_wins']} | Emp: {m['draws']}", True, BLANCO), (px,100))

            screen.blit(fuente_small.render(f"TD gana: {m['td_wins']} | Rival: {m['opp_wins']} | Emp: {m['draws']}", True, BLANCO), (px,100))

            #NUEVO: cálculo y visualización del winrate del TD
            if m["games"] > 0:
                winrate_td = (m["td_wins"] / m["games"]) * 100
                screen.blit(fuente_small.render(f"Winrate TD: {winrate_td:.1f}%", True, BLANCO), (px,130))

            screen.blit(fuente_small.render(f"Estados aprendidos: {len(td.V)}", True, BLANCO), (px,170))
            screen.blit(fuente_small.render(f"Último mov TD: {ultimo_mov_td}", True, BLANCO), (px,200))
            screen.blit(fuente_small.render(f"Valor V(s): {valor_estado_actual:.3f}", True, BLANCO), (px,230))
            screen.blit(fuente_small.render(f"Epsilon: {epsilon_actual:.2f}", True, BLANCO), (px,260))

            screen.blit(fuente_small.render(f"Estados aprendidos: {len(td.V)}", True, BLANCO), (px,170))
            screen.blit(fuente_small.render(f"Último mov TD: {ultimo_mov_td}", True, BLANCO), (px,200))
            screen.blit(fuente_small.render(f"Valor V(s): {valor_estado_actual:.3f}", True, BLANCO), (px,230))
            screen.blit(fuente_small.render(f"Epsilon: {epsilon_actual:.2f}", True, BLANCO), (px,260))

            #ficha fantasma del jugador humano
            if not game_over and player_roles.get(turno)==ROLE_HUMANO:
                pygame.draw.circle(screen, ROJO,
                    (int(columna_actual*SQUARESIZE+SQUARESIZE/2), int(SQUARESIZE/2)), RADIUS)

            #pintar fichas ganadoras
            if posiciones_ganadoras:
                dibujar_linea_ganadora(screen, posiciones_ganadoras, width, height)

            pygame.display.update()

            #reinicio automático (solo IA vs IA)
            if game_over and auto_restart:
                if apprentice_mark is not None:
                    resultado = td.obtener_recompensa(tablero, apprentice_mark)
                    td.actualizar_td(resultado)
                    registrar_resultado_stats(stats, game_mode, player_roles, ultimo_ganador)

                pygame.time.wait(150)
                nueva_partida()

        clock.tick(60)

if __name__=="__main__":
    main()
