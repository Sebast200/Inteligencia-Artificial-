import numpy as np
import pygame
import sys
import math
import time
import random
import os
import pickle

# -------- CONFIGURACIÓN GENERAL --------

ROW_COUNT = 6
COLUMN_COUNT = 7
SQUARESIZE = 100
RADIUS = int(SQUARESIZE / 2 - 8)

# Colores
AZUL = (25, 75, 255)
NEGRO = (20, 20, 20)
ROJO = (230, 60, 60)
AMARILLO = (250, 230, 40)
BLANCO = (240, 240, 240)
VERDE = (0, 255, 0)

# Jugadores en el tablero
J1 = 1   # Rojo
J2 = 2   # Amarillo

# Roles de agente
ROLE_HUMANO          = "human"
ROLE_TD              = "td"
ROLE_MINIMAX_PERF    = "minimax_perfect"
ROLE_MINIMAX_SEMI    = "minimax_semi"

# Configuración IA TD
ALPHA = 0.1
EPSILON_HUMAN = 0.1   # Exploración cuando juega vs humano
EPSILON_TRAIN = 0.2   # Exploración cuando entrena vs otras IAs

# Archivos persistentes
VALUES_FILE = "td_values.pkl"    # valores de TD
STATS_FILE  = "td_stats.pkl"     # estadísticas globales

# Profundidad de Minimax
MAX_DEPTH = 4

# Probabilidad de error en IA semiperfecta
ERROR_PROB = 0.25

# -------- ESTADO GLOBAL --------
V = {}                         # Diccionario de valores TD
episode_states = []            # Estados visitados por la IA aprendiz en una partida
apprentice_mark = None         # 1 ó 2, quién es el aprendiz en el tablero
game_mode = None               # 1,2,3 según menú
auto_restart = False           # Si las partidas se encadenan solas (IA vs IA)
player_roles = {}              # {J1: role, J2: role}
ganador_texto = ""
ultimo_ganador = None

# Estadísticas en memoria (además de V)
def default_stats():
    return {
        "total_games": 0,
        1: {"games": 0, "td_wins": 0, "opp_wins": 0, "draws": 0},
        2: {"games": 0, "td_wins": 0, "opp_wins": 0, "draws": 0},
        3: {"games": 0, "td_wins": 0, "opp_wins": 0, "draws": 0},
    }

stats = default_stats()

# Contadores sesión actual (solo visual)
num_games = 0
victorias_j1 = 0
victorias_j2 = 0

# Info de depuración / aprendizaje
ultimo_mov_td = "-"
valor_estado_actual = 0.0
epsilon_actual = 0.0

# -------- FUNCIONES BÁSICAS DEL JUEGO --------

def crear_tablero():
    return np.zeros((ROW_COUNT, COLUMN_COUNT))

def soltar_pieza(tablero, fila, col, pieza):
    tablero[fila][col] = pieza

def movimiento_valido(tablero, col):
    return tablero[ROW_COUNT - 1][col] == 0

def siguiente_fila_vacia(tablero, col):
    for r in range(ROW_COUNT):
        if tablero[r][col] == 0:
            return r

def tablero_lleno(tablero):
    for c in range(COLUMN_COUNT):
        if tablero[ROW_COUNT - 1][c] == 0:
            return False
    return True

def verificar_ganador(tablero, pieza):
    # Horizontal
    for c in range(COLUMN_COUNT - 3):
        for r in range(ROW_COUNT):
            if all(tablero[r][c+i] == pieza for i in range(4)):
                return [(r, c+i) for i in range(4)]

    # Vertical
    for c in range(COLUMN_COUNT):
        for r in range(ROW_COUNT - 3):
            if all(tablero[r+i][c] == pieza for i in range(4)):
                return [(r+i, c) for i in range(4)]

    # Diagonal positiva
    for c in range(COLUMN_COUNT - 3):
        for r in range(ROW_COUNT - 3):
            if all(tablero[r+i][c+i] == pieza for i in range(4)):
                return [(r+i, c+i) for i in range(4)]

    # Diagonal negativa
    for c in range(COLUMN_COUNT - 3):
        for r in range(3, ROW_COUNT):
            if all(tablero[r-i][c+i] == pieza for i in range(4)):
                return [(r-i, c+i) for i in range(4)]

    return None

def dibujar_tablero(tablero):
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

def animar_caida(col, fila_final, color):
    for f in range(ROW_COUNT):
        if f > fila_final:
            break
        dibujar_tablero(tablero)
        pygame.draw.circle(screen, color,
            (int(col*SQUARESIZE+SQUARESIZE/2),
             int(SQUARESIZE/2 + (f+1)*SQUARESIZE)),
            RADIUS)
        pygame.display.update()
        time.sleep(0.04)

def dibujar_linea_ganadora(lista):
    for (r, c) in lista:
        pygame.draw.circle(
            screen, VERDE,
            (int(c*SQUARESIZE + SQUARESIZE/2),
             height - int(r*SQUARESIZE + SQUARESIZE/2)),
            RADIUS
        )

# -------- TABLEROS INICIALES ALEATORIOS --------

def generar_tablero_partida_real():
    """
    Simula una partida real alternando J1 y J2 hasta cierto punto,
    asegurando que el tablero no esté ganado ni lleno.
    """
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

# -------- FONDO DEGRADADO PANEL DERECHO --------

def dibujar_degradado_vertical(surface, rect, c1, c2):
    x, y, w, h = rect
    for i in range(h):
        f = i / h
        r = int(c1[0]*(1-f) + c2[0]*f)
        g = int(c1[1]*(1-f) + c2[1]*f)
        b = int(c1[2]*(1-f) + c2[2]*f)
        pygame.draw.line(surface, (r,g,b), (x, y+i), (x+w, y+i))

# -------- IA MINIMAX --------

def get_valid_locations(tablero):
    return [c for c in range(COLUMN_COUNT) if movimiento_valido(tablero, c)]

def is_terminal(tablero):
    return (
        verificar_ganador(tablero, J1) is not None
        or verificar_ganador(tablero, J2) is not None
        or tablero_lleno(tablero)
    )

def evaluar_ventana(v, pieza):
    puntuacion = 0
    oponente = J1 if pieza == J2 else J2

    if v.count(pieza) == 4: puntuacion += 100
    elif v.count(pieza) == 3 and v.count(0) == 1: puntuacion += 10
    elif v.count(pieza) == 2 and v.count(0) == 2: puntuacion += 4

    if v.count(oponente) == 3 and v.count(0) == 1:
        puntuacion -= 8

    return puntuacion

def score_position(tablero, pieza):
    score = 0
    center = [int(i) for i in list(tablero[:, COLUMN_COUNT//2])]
    score += center.count(pieza) * 6

    # Horizontal
    for r in range(ROW_COUNT):
        row = [int(i) for i in tablero[r, :]]
        for c in range(COLUMN_COUNT - 3):
            score += evaluar_ventana(row[c:c+4], pieza)

    # Vertical
    for c in range(COLUMN_COUNT):
        col = [int(i) for i in tablero[:, c]]
        for r in range(ROW_COUNT - 3):
            score += evaluar_ventana(col[r:r+4], pieza)

    # Diagonal positiva
    for r in range(ROW_COUNT - 3):
        for c in range(COLUMN_COUNT - 3):
            score += evaluar_ventana([tablero[r+i][c+i] for i in range(4)], pieza)

    # Diagonal negativa
    for r in range(3, ROW_COUNT):
        for c in range(COLUMN_COUNT - 3):
            score += evaluar_ventana([tablero[r-i][c+i] for i in range(4)], pieza)

    return score

def minimax(tablero, depth, alpha, beta, maximizing, pieza_max):
    valid = get_valid_locations(tablero)
    terminal = is_terminal(tablero)

    if depth == 0 or terminal:
        if terminal:
            if verificar_ganador(tablero, pieza_max):
                return (None, 1_000_000)
            elif verificar_ganador(tablero, J1 if pieza_max == J2 else J2):
                return (None, -1_000_000)
            return (None, 0)
        return (None, score_position(tablero, pieza_max))

    if maximizing:
        value = -math.inf
        best_col = random.choice(valid)
        for col in valid:
            fila = siguiente_fila_vacia(tablero, col)
            copia = tablero.copy()
            soltar_pieza(copia, fila, col, pieza_max)
            new_score = minimax(copia, depth-1, alpha, beta, False, pieza_max)[1]
            if new_score > value:
                value = new_score
                best_col = col
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return best_col, value
    else:
        value = math.inf
        pieza_min = J1 if pieza_max == J2 else J2
        best_col = random.choice(valid)
        for col in valid:
            fila = siguiente_fila_vacia(tablero, col)
            copia = tablero.copy()
            soltar_pieza(copia, fila, col, pieza_min)
            new_score = minimax(copia, depth-1, alpha, beta, True, pieza_max)[1]
            if new_score < value:
                value = new_score
                best_col = col
            beta = min(beta, value)
            if alpha >= beta:
                break
        return best_col, value

# -------- PERSISTENCIA TD & STATS --------

def cargar_valores():
    global V
    if os.path.exists(VALUES_FILE):
        try:
            with open(VALUES_FILE, "rb") as f:
                V = pickle.load(f)
        except Exception:
            V = {}
    else:
        V = {}

def guardar_valores():
    with open(VALUES_FILE, "wb") as f:
        pickle.dump(V, f)

def cargar_stats():
    global stats
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "rb") as f:
                stats = pickle.load(f)
        except Exception:
            stats = default_stats()
    else:
        stats = default_stats()

def guardar_stats():
    with open(STATS_FILE, "wb") as f:
        pickle.dump(stats, f)

def registrar_resultado_stats(winner_mark):
    """Actualiza estadísticas globales persistentes."""
    if game_mode not in (1,2,3):
        return
    stats["total_games"] += 1
    m = stats[game_mode]
    m["games"] += 1

    if winner_mark is None:
        m["draws"] += 1
    else:
        role = player_roles.get(winner_mark)
        if role == ROLE_TD:
            m["td_wins"] += 1
        else:
            m["opp_wins"] += 1

    guardar_stats()

# -------- TD LEARNING (APRENDIZ) --------

def get_state_key(tablero, mark):
    # Aplanar tablero y añadir quién es el aprendiz (1 ó 2)
    flat = tablero.flatten().astype(int)
    return "".join(map(str, flat)) + f"_{mark}"

def actualizar_td(reward):
    global episode_states, V
    for key in episode_states:
        old = V.get(key, 0.0)
        V[key] = old + ALPHA * (reward - old)
    episode_states = []
    guardar_valores()

def td_elegir_movimiento(tablero, mark, epsilon):
    """Devuelve (columna, tipo_movimiento) donde tipo_movimiento es 'exploración' o 'explotación'."""
    valid_cols = get_valid_locations(tablero)
    if not valid_cols:
        return None, "-"

    # Exploración
    if random.random() < epsilon:
        return random.choice(valid_cols), "exploración"

    # Explotación: elegir acción que lleve a estado con mejor valor
    mejor_val = -1e9
    mejores_cols = []
    for col in valid_cols:
        fila = siguiente_fila_vacia(tablero, col)
        copia = tablero.copy()
        soltar_pieza(copia, fila, col, mark)
        key = get_state_key(copia, mark)
        v = V.get(key, 0.0)
        if v > mejor_val:
            mejor_val = v
            mejores_cols = [col]
        elif v == mejor_val:
            mejores_cols.append(col)

    if not mejores_cols:
        return random.choice(valid_cols), "exploración"
    return random.choice(mejores_cols), "explotación"

# -------- GESTIÓN DE MODOS Y PARTIDAS --------

def configurar_modo(modo):
    global game_mode, player_roles, apprentice_mark, auto_restart, num_games
    game_mode = modo
    num_games = 0
    if modo == 1:
        # IA Aprendiz (amarillo) vs Humano (rojo)
        player_roles = {J1: ROLE_HUMANO, J2: ROLE_TD}
        apprentice_mark = J2
        auto_restart = False
    elif modo == 2:
        # IA Aprendiz (rojo) vs IA Perfecta (amarillo)
        player_roles = {J1: ROLE_TD, J2: ROLE_MINIMAX_PERF}
        apprentice_mark = J1
        auto_restart = True
    elif modo == 3:
        # IA Aprendiz (rojo) vs IA Semiperfecta (amarillo)
        player_roles = {J1: ROLE_TD, J2: ROLE_MINIMAX_SEMI}
        apprentice_mark = J1
        auto_restart = True

def nueva_partida():
    global tablero, turno, posiciones_ganadoras, game_over, episode_states
    global ultimo_mov_td, valor_estado_actual, epsilon_actual
    episode_states = []
    tablero, turno = generar_tablero_partida_real()
    posiciones_ganadoras = None
    game_over = False
    ultimo_mov_td = "-"
    valor_estado_actual = 0.0
    epsilon_actual = 0.0
    dibujar_tablero(tablero)

def obtener_texto_ganador(winner_mark):
    if winner_mark is None:
        return "Empate"
    role = player_roles.get(winner_mark, "?")
    if role == ROLE_HUMANO:
        return "¡Gana el Humano!"
    elif role == ROLE_TD:
        return "Gana la IA Aprendiz"
    elif role == ROLE_MINIMAX_PERF:
        return "Gana la IA Perfecta"
    elif role == ROLE_MINIMAX_SEMI:
        return "Gana la IA Semiperfecta"
    else:
        return "Gana alguien"

def fin_partida(winner_mark):
    global game_over, ultimo_ganador, victorias_j1, victorias_j2, ganador_texto, num_games
    game_over = True
    ultimo_ganador = winner_mark
    num_games += 1

    if winner_mark == J1:
        victorias_j1 += 1
    elif winner_mark == J2:
        victorias_j2 += 1

    # Recompensa TD
    if apprentice_mark is not None:
        if winner_mark is None:
            reward = 0.0
        elif winner_mark == apprentice_mark:
            reward = 1.0
        else:
            reward = -1.0
        if episode_states:
            actualizar_td(reward)

    registrar_resultado_stats(winner_mark)
    ganador_texto = obtener_texto_ganador(winner_mark)

# -------- MENÚ PRINCIPAL --------

def dibujar_menu():
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

    # Mostrar estadísticas globales resumidas
    y0 = 160
    x_stats = width//2 + 40
    screen.blit(fuente_small.render("Estadísticas globales:", True, BLANCO), (x_stats, y0-30))
    screen.blit(fuente_small.render(f"Total partidas: {stats['total_games']}", True, BLANCO), (x_stats, y0))

    for modo in (1,2,3):
        m = stats[modo]
        txt = f"Modo {modo} - Partidas: {m['games']} | TD gana: {m['td_wins']} | Rival: {m['opp_wins']} | Emp: {m['draws']}"
        screen.blit(fuente_small.render(txt, True, BLANCO), (x_stats, y0 + 30*modo))

    pygame.display.update()

# -------- INIT PYGAME --------

pygame.init()
width = COLUMN_COUNT * SQUARESIZE + 400
height = (ROW_COUNT + 1) * SQUARESIZE
screen = pygame.display.set_mode((width, height))
pygame.display.setCaption = pygame.display.set_caption("Conecta 4 - TD Learning")

fuente = pygame.font.SysFont("arial", 45, bold=True)
fuente_small = pygame.font.SysFont("arial", 22, bold=False)

# Cargar valores TD y estadísticas persistentes
cargar_valores()
cargar_stats()

# Estado inicial: menú
state = "menu"
tablero = crear_tablero()
turno = J1
posiciones_ganadoras = None
game_over = False
columna_actual = COLUMN_COUNT // 2

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

# -------- LOOP PRINCIPAL --------

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
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
                        animar_caida(columna_actual, fila, ROJO)
                        soltar_pieza(tablero, fila, columna_actual, J1)

                        gan = verificar_ganador(tablero, J1)
                        if gan:
                            posiciones_ganadoras = gan
                            fin_partida(J1)
                        elif tablero_lleno(tablero):
                            fin_partida(None)
                        else:
                            turno = J2

                        dibujar_tablero(tablero)
                        if game_over and not auto_restart:
                            continue

            # Reinicio en modo humano (espacio)
            if event.type == pygame.KEYDOWN and game_mode == 1 and game_over:
                if event.key == pygame.K_SPACE:
                    nueva_partida()

    # LÓGICA FUERA DE EVENTOS
    if state == "menu":
        dibujar_menu()
        continue

    # Si estamos en juego:
    if state == "game":
        # Turno IA Aprendiz (TD)
        if not game_over and player_roles.get(turno) == ROLE_TD:
            pygame.time.wait(120)
            # Registrar estado actual para TD
            key = get_state_key(tablero, apprentice_mark)
            episode_states.append(key)

            epsilon = EPSILON_TRAIN if game_mode in (2, 3) else EPSILON_HUMAN
            col, tipo = td_elegir_movimiento(tablero, apprentice_mark, epsilon)
            if col is not None and movimiento_valido(tablero, col):
                fila = siguiente_fila_vacia(tablero, col)
                color = ROJO if apprentice_mark == J1 else AMARILLO
                animar_caida(col, fila, color)
                soltar_pieza(tablero, fila, col, apprentice_mark)

                # Info de depuración
                ultimo_mov_td = tipo
                epsilon_actual = epsilon
                key2 = get_state_key(tablero, apprentice_mark)
                valor_estado_actual = V.get(key2, 0.0)
                episode_states.append(key2)

                gan = verificar_ganador(tablero, apprentice_mark)
                if gan:
                    posiciones_ganadoras = gan
                    fin_partida(apprentice_mark)
                elif tablero_lleno(tablero):
                    fin_partida(None)
                else:
                    turno = J1 if apprentice_mark == J2 else J2

                dibujar_tablero(tablero)

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
                animar_caida(col, fila, color)
                soltar_pieza(tablero, fila, col, turno)

                gan = verificar_ganador(tablero, turno)
                if gan:
                    posiciones_ganadoras = gan
                    fin_partida(turno)
                elif tablero_lleno(tablero):
                    fin_partida(None)
                else:
                    turno = J1 if turno == J2 else J2

                dibujar_tablero(tablero)

        # DIBUJO HUD SUPERIOR + PANEL DERECHO
        pygame.draw.rect(screen, NEGRO, (0, 0, width, SQUARESIZE))

        # Mensaje de ganador (modo humano o no, solo informativo)
        if game_over:
            if ultimo_ganador is None:
                color_txt = BLANCO
            else:
                color_txt = ROJO if ultimo_ganador == J1 else AMARILLO
            text_g = fuente.render(ganador_texto, True, color_txt)
            screen.blit(text_g, (10, 5))
            if not auto_restart and game_mode == 1:
                text_r = fuente_small.render("Presiona ESPACIO para siguiente partida", True, BLANCO)
                screen.blit(text_r, (10, 50))

        # Panel derecho
        panel_rect = (COLUMN_COUNT*SQUARESIZE, 0, width-COLUMN_COUNT*SQUARESIZE, height)
        dibujar_degradado_vertical(screen, panel_rect, (40,40,40), (0,0,0))
        px = COLUMN_COUNT * SQUARESIZE + 20

        # Stats persistentes del modo actual
        m = stats.get(game_mode, {"games":0,"td_wins":0,"opp_wins":0,"draws":0})
        total_modo = max(1, m["games"])
        winrate = 100.0 * m["td_wins"] / total_modo

        screen.blit(fuente_small.render(f"Modo: {mode_labels.get(game_mode,'')}", True, BLANCO), (px, 10))
        screen.blit(fuente_small.render(f"Partida sesión: {num_games}", True, BLANCO), (px, 40))
        screen.blit(fuente_small.render(f"Partidas totales (modo): {m['games']}", True, BLANCO), (px, 70))
        screen.blit(fuente_small.render(f"TD gana: {m['td_wins']} | Rival: {m['opp_wins']} | Emp: {m['draws']}", True, BLANCO), (px, 100))
        screen.blit(fuente_small.render(f"Winrate TD: {winrate:.1f}%", True, BLANCO), (px, 130))

        screen.blit(fuente_small.render(f"Estados aprendidos: {len(V)}", True, BLANCO), (px, 170))
        screen.blit(fuente_small.render(f"Último mov TD: {ultimo_mov_td}", True, BLANCO), (px, 200))
        screen.blit(fuente_small.render(f"Valor V(s): {valor_estado_actual:.3f}", True, BLANCO), (px, 230))
        screen.blit(fuente_small.render(f"Epsilon: {epsilon_actual:.2f}", True, BLANCO), (px, 260))

        # Ficha fantasma para humano (solo modo humano)
        if not game_over and player_roles.get(turno) == ROLE_HUMANO:
            pygame.draw.circle(screen, ROJO,
                (int(columna_actual*SQUARESIZE+SQUARESIZE/2), int(SQUARESIZE/2)), RADIUS)

        # Línea ganadora
        if posiciones_ganadoras:
            dibujar_linea_ganadora(posiciones_ganadoras)

        pygame.display.update()

        # Auto-reinicio en modos IA vs IA
        if game_over and auto_restart:
            pygame.time.wait(150)
            nueva_partida()
