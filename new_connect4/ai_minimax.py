#ai_minimax.py es el archivo que contiene la implementacion
#del algoritmo Minimax con poda Alpha-Beta para el juego Conecta 4
import math
import random

#se importan las funciones y variables necesarias del juego
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


#---funciones auxiliares
#este metodo obtiene las columnas validas para jugar
def get_valid_locations(tablero):
    #devuelve una lista con todas las columnas que no se encuentren llenas
    return [c for c in range(COLUMN_COUNT) if movimiento_valido(tablero, c)]

#este metodo verifica si la partida ha terminado
def is_terminal(tablero):
    #devuelve True si hay un ganador o si el tablero esta lleno
    return (
        verificar_ganador(tablero, J1) is not None or
        verificar_ganador(tablero, J2) is not None or
        tablero_lleno(tablero)
    )

#este metodo evalua una ventana de 4 posiciones o fichas
def evaluar_ventana(v, pieza):
    #se declara la variable puntuacion que sirve para acumular la puntuacion de la ventana
    #la puntuacion sirve para evaluar que tan buena es la ventana para la pieza dada
    puntuacion = 0
    #se determina cual es la pieza del oponente
    oponente = J1 if pieza == J2 else J2
    #si la ventana tiene 4 fichas iguales a la pieza, se suma 100 puntos
    if v.count(pieza) == 4:
        puntuacion += 100
    #sino, si tiene 3 fichas iguales y un espacio vacio, se suman 10 puntos
    elif v.count(pieza) == 3 and v.count(0) == 1:
        puntuacion += 10
    #sino, si tiene 2 fichas iguales y 2 espacios vacios, se suman 4 puntos
    elif v.count(pieza) == 2 and v.count(0) == 2:
        puntuacion += 4

    #si la ventana tiene 3 fichas del oponente y un espacio vacio, se restan 8 puntos
    if v.count(oponente) == 3 and v.count(0) == 1:
        puntuacion -= 8
    #se retona la puntuacion calculada
    return puntuacion

#este metodo evalua el tablero completo usando heuristica
def score_position(tablero, pieza):
    #se declara la variable score que acumula la puntuacion total del tablero
    score = 0
    #en cuanto a la evaluacion, se le da mas importancia a las fichas en el centro
    #porque permiten mas posibilidades de formar conexiones
    #esta variable es para evaluar la columna central
    center_column = [int(i) for i in list(tablero[:, COLUMN_COUNT // 2])]
    #esta variable es para sumar puntos por tener fichas en la columna central
    score += center_column.count(pieza) * 6

    #evualuacion horizontal
    #aqui se revisan todos los grupos de 4 horizontales
    for r in range(ROW_COUNT):
        row = [int(i) for i in tablero[r, :]]
        for c in range(COLUMN_COUNT - 3):
            window = row[c:c+4]
            score += evaluar_ventana(window, pieza)

    #evualuacion vertical
    #aqui se revisan todos los grupos de 4 verticales
    for c in range(COLUMN_COUNT):
        col = [int(i) for i in tablero[:, c]]
        for r in range(ROW_COUNT - 3):
            window = col[r:r+4]
            score += evaluar_ventana(window, pieza)

    #evaluacion diagonal positiva (/)
    for r in range(ROW_COUNT - 3):
        for c in range(COLUMN_COUNT - 3):
            window = [tablero[r+i][c+i] for i in range(4)]
            score += evaluar_ventana(window, pieza)

    #evualuacion diagonal negativa (\)
    for r in range(3, ROW_COUNT):
        for c in range(COLUMN_COUNT - 3):
            window = [tablero[r-i][c+i] for i in range(4)]
            score += evaluar_ventana(window, pieza)
    #devuelve la puntuacion total del tablero
    return score


#---minimax con poda alfa-beta
#este metodo implementa el algoritmo minimax con poda alfa-beta
def minimax(tablero, depth, alpha, beta, maximizing, pieza_max):
    #primero se obtienen las columnas validas y si el nodo es terminal
    valid = get_valid_locations(tablero)
    terminal = is_terminal(tablero)

    #si la profundidad es 0 o el nodo es terminal, se evalua el tablero
    if depth == 0 or terminal:
        #si es un nodo terminal, se asigna una puntuacion alta o baja segun el resultado
        if terminal:
            #si hay un ganador, se asigna una puntuacion alta o baja
            if verificar_ganador(tablero, pieza_max):
                return (None, 1_000_000)
            #sino, si el oponente gano, se asigna una puntuacion baja
            elif verificar_ganador(tablero, J1 if pieza_max == J2 else J2):
                return (None, -1_000_000)
            #sino, es un empate
            else:
                return (None, 0)
        #si no es terminal, se evalua el tablero con la funcion heuristica
        else:
            return (None, score_position(tablero, pieza_max))

    #si es el turno del MAXIMIZADOR
    if maximizing:
        value = -math.inf
        best_col = random.choice(valid)
        #para cada columna valida
        for col in valid:
            fila = siguiente_fila_vacia(tablero, col)
            copia = tablero.copy()
            copia[fila][col] = pieza_max
            #se simula el movimiento y vuelve a llamar a minimax
            new_score = minimax(copia, depth - 1, alpha, beta, False, pieza_max)[1]
            #si el movimiento es mejor, entonces se actualiza el mejor valor y la mejor columna
            if new_score > value:
                value = new_score
                best_col = col
            #luego de eso, se aplica la poda alfa-beta
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        #y devuelve columna y valor
        return best_col, value

    #---minimizador
    #esto es igual que MAX, pero busca minimizar
    #(esta se actualiza con encuentra un valor menor)
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
