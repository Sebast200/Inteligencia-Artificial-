import math
import random

from game import (
    ROW_COUNT,
    COLUMN_COUNT,
    J1,
    J2,
    movimiento_valido,
    siguiente_fila_vacia,
    verificar_ganador,
    tablero_lleno
)


# -------- FUNCIONES AUXILIARES --------

def get_valid_locations(tablero):
    """Devuelve la lista de columnas donde se puede jugar."""
    return [c for c in range(COLUMN_COUNT) if movimiento_valido(tablero, c)]


def is_terminal(tablero):
    """Determina si la partida ha terminado."""
    return (
        verificar_ganador(tablero, J1) is not None or
        verificar_ganador(tablero, J2) is not None or
        tablero_lleno(tablero)
    )


def evaluar_ventana(v, pieza):
    """Evalúa una ventana (lista de 4 valores) según heurística estándar."""
    puntuacion = 0
    oponente = J1 if pieza == J2 else J2

    if v.count(pieza) == 4:
        puntuacion += 100
    elif v.count(pieza) == 3 and v.count(0) == 1:
        puntuacion += 10
    elif v.count(pieza) == 2 and v.count(0) == 2:
        puntuacion += 4

    # Penalización si el rival tiene 3 y un hueco
    if v.count(oponente) == 3 and v.count(0) == 1:
        puntuacion -= 8

    return puntuacion


def score_position(tablero, pieza):
    """Evalúa el tablero completo usando heurística."""
    score = 0

    # Centro (más valioso)
    center_column = [int(i) for i in list(tablero[:, COLUMN_COUNT // 2])]
    score += center_column.count(pieza) * 6

    # Horizontal
    for r in range(ROW_COUNT):
        row = [int(i) for i in tablero[r, :]]
        for c in range(COLUMN_COUNT - 3):
            window = row[c:c+4]
            score += evaluar_ventana(window, pieza)

    # Vertical
    for c in range(COLUMN_COUNT):
        col = [int(i) for i in tablero[:, c]]
        for r in range(ROW_COUNT - 3):
            window = col[r:r+4]
            score += evaluar_ventana(window, pieza)

    # Diagonal (+)
    for r in range(ROW_COUNT - 3):
        for c in range(COLUMN_COUNT - 3):
            window = [tablero[r+i][c+i] for i in range(4)]
            score += evaluar_ventana(window, pieza)

    # Diagonal (-)
    for r in range(3, ROW_COUNT):
        for c in range(COLUMN_COUNT - 3):
            window = [tablero[r-i][c+i] for i in range(4)]
            score += evaluar_ventana(window, pieza)

    return score


# -------- MINIMAX CON PODA ALPHA-BETA --------

def minimax(tablero, depth, alpha, beta, maximizing, pieza_max):
    """
    Devuelve (columna, valor).
    pieza_max = pieza para la cual queremos maximizar.
    """
    valid = get_valid_locations(tablero)
    terminal = is_terminal(tablero)

    # Nodos terminales o profundidad 0
    if depth == 0 or terminal:
        if terminal:
            if verificar_ganador(tablero, pieza_max):
                return (None, 1_000_000)
            elif verificar_ganador(tablero, J1 if pieza_max == J2 else J2):
                return (None, -1_000_000)
            else:
                return (None, 0)
        else:
            return (None, score_position(tablero, pieza_max))

    # MAXIMIZADOR
    if maximizing:
        value = -math.inf
        best_col = random.choice(valid)

        for col in valid:
            fila = siguiente_fila_vacia(tablero, col)
            copia = tablero.copy()
            copia[fila][col] = pieza_max

            new_score = minimax(copia, depth - 1, alpha, beta, False, pieza_max)[1]

            if new_score > value:
                value = new_score
                best_col = col

            alpha = max(alpha, value)
            if alpha >= beta:
                break

        return best_col, value

    # MINIMIZADOR
    else:
        value = math.inf
        pieza_min = J1 if pieza_max == J2 else J2
        best_col = random.choice(valid)

        for col in valid:
            fila = siguiente_fila_vacia(tablero, col)
            copia = tablero.copy()
            copia[fila][col] = pieza_min

            new_score = minimax(copia, depth - 1, alpha, beta, True, pieza_max)[1]

            if new_score < value:
                value = new_score
                best_col = col

            beta = min(beta, value)
            if alpha >= beta:
                break

        return best_col, value
