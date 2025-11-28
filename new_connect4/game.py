#game.py es el archivo que contiene las funciones básicas del juego Conecta 4
import numpy as np #para manejar matrices

#tamaño del tablero
ROW_COUNT = 6
COLUMN_COUNT = 7

#jugadores
J1 = 1
J2 = 2


#de aqui para abajo se encuentran las funciones del juego

#este metodo crea el tablero
def crear_tablero():
    #en terminos de logica, va a devolver una matriz NumPy de el tamaño de
    #ROW_COUNT x COLUMN_COUNT llena de ceros. dentro de estas las celdas
    #iran cambiando de valor para representar las piezas de los jugadores
    #(0 es vacio, 1 es jugador 1, 2 es jugador 2)
    return np.zeros((ROW_COUNT, COLUMN_COUNT))

#este metodo sirve para soltar una pieza en la posicion especificada
#la verificacion de si se puede hacer dicho movimiento se hace en la funcion de abajo
def soltar_pieza(tablero, fila, col, pieza):
    tablero[fila][col] = pieza

#este metodo revisa si el movimiento es valido (tipo si la columna no esta llena)
def movimiento_valido(tablero, col):
    #si la fila mas alta de la columna es 0, significa que hay espacio
    return tablero[ROW_COUNT - 1][col] == 0

#este metodo obtiene la fila mas baja disponible en la columna
def siguiente_fila_vacia(tablero, col):
    #busca de abajo hacia arriba cual es la primera fila vacia en esa columna
    for r in range(ROW_COUNT):
        if tablero[r][col] == 0:
            return r
    #si esta llena la columna, devuelve None
    return None  

#este metodo sirve para revisar si el tablero esta lleno
def tablero_lleno(tablero):
    #revisa arriba de cada columna si hay espacio
    for c in range(COLUMN_COUNT):
        #si hay espacio en alguna columna, devuelve False y se sale del proceso
        if tablero[ROW_COUNT - 1][c] == 0:
            return False
    #si no encontro espacio en ninguna columna, devuelve True
    return True

#este metodo revisa si hay un ganador en el tablero, verificando todas las posibles combinaciones
def verificar_ganador(tablero, pieza):
    #para combinaciones horizontales
    for c in range(COLUMN_COUNT - 3):
        for r in range(ROW_COUNT):
            if all(tablero[r][c+i] == pieza for i in range(4)):
                return [(r, c+i) for i in range(4)]

    #para combinaciones verticales
    for c in range(COLUMN_COUNT):
        for r in range(ROW_COUNT - 3):
            if all(tablero[r+i][c] == pieza for i in range(4)):
                return [(r+i, c) for i in range(4)]

    #para combinaciones diagonales positivas (se ven asi /)
    for c in range(COLUMN_COUNT - 3):
        for r in range(ROW_COUNT - 3):
            if all(tablero[r+i][c+i] == pieza for i in range(4)):
                return [(r+i, c+i) for i in range(4)]

    #para combinaciones diagonales negativas (se ven asi \)
    for c in range(COLUMN_COUNT - 3):
        for r in range(3, ROW_COUNT):
            if all(tablero[r-i][c+i] == pieza for i in range(4)):
                return [(r-i, c+i) for i in range(4)]
    #si no hay ganador, devuelve None
    return None
