import numpy as np
import pygame
import sys
import math
import time

# -------- CONFIGURACIÓN --------
ROW_COUNT = 6
#COLUMN_COUNT es la cantidad de columnas que presentara el juego
COLUMN_COUNT = 7
SQUARESIZE = 100
RADIUS = int(SQUARESIZE / 2 - 8)

# Colores
AZUL = (25, 75, 255)
NEGRO = (20, 20, 20)
ROJO = (230, 60, 60)
AMARILLO = (250, 230, 40)
BLANCO = (240, 240, 240)

# -------- FUNCIONES DEL JUEGO --------
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

def verificar_ganador(tablero, pieza):
    # Horizontal
    for c in range(COLUMN_COUNT - 3):
        for r in range(ROW_COUNT):
            if all(tablero[r][c + i] == pieza for i in range(4)):
                return True
    # Vertical
    for c in range(COLUMN_COUNT):
        for r in range(ROW_COUNT - 3):
            if all(tablero[r + i][c] == pieza for i in range(4)):
                return True
    # Diagonal positiva
    for c in range(COLUMN_COUNT - 3):
        for r in range(ROW_COUNT - 3):
            if all(tablero[r + i][c + i] == pieza for i in range(4)):
                return True
    # Diagonal negativa
    for c in range(COLUMN_COUNT - 3):
        for r in range(3, ROW_COUNT):
            if all(tablero[r - i][c + i] == pieza for i in range(4)):
                return True
    return False

def dibujar_tablero(tablero):
    for c in range(COLUMN_COUNT):
        for r in range(ROW_COUNT):
            pygame.draw.rect(screen, AZUL, (c * SQUARESIZE, (r + 1) * SQUARESIZE, SQUARESIZE, SQUARESIZE))
            pygame.draw.circle(screen, NEGRO, (int(c * SQUARESIZE + SQUARESIZE / 2), int((r + 1) * SQUARESIZE + SQUARESIZE / 2)), RADIUS)

    for c in range(COLUMN_COUNT):
        for r in range(ROW_COUNT):
            if tablero[r][c] == 1:
                pygame.draw.circle(screen, ROJO, (int(c * SQUARESIZE + SQUARESIZE / 2), height - int(r * SQUARESIZE + SQUARESIZE / 2)), RADIUS)
            elif tablero[r][c] == 2:
                pygame.draw.circle(screen, AMARILLO, (int(c * SQUARESIZE + SQUARESIZE / 2), height - int(r * SQUARESIZE + SQUARESIZE / 2)), RADIUS)
    pygame.display.update()

def animar_caida(col, fila_final, color):
    """Anima la caída de la ficha"""
    for f in range(ROW_COUNT):
        if f > fila_final:
            break
        dibujar_tablero(tablero)
        pygame.draw.circle(screen, color, (int(col * SQUARESIZE + SQUARESIZE / 2),
                                           int(SQUARESIZE / 2 + (f + 1) * SQUARESIZE)), RADIUS)
        pygame.display.update()
        time.sleep(0.04)

def reiniciar_juego():
    """Reinicia el estado del juego"""
    global tablero, turno, game_over, ganador_texto
    tablero = crear_tablero()
    turno = 0
    game_over = False
    ganador_texto = None
    dibujar_tablero(tablero)
    pygame.draw.rect(screen, NEGRO, (0, 0, width, SQUARESIZE))
    pygame.display.update()

# -------- MAIN LOOP --------
tablero = crear_tablero()
game_over = False
turno = 0

pygame.init()
#que pasa si cambio esto? la configuracion por defecto es:
#width = COLUMN_COUNTE * SQUARESIZE
width = COLUMN_COUNT * SQUARESIZE + 500
height = (ROW_COUNT + 1) * SQUARESIZE
size = (width, height)
#quiero agregar una variable que cuente la cantidad de partidas
num_games = 1

screen = pygame.display.set_mode(size)
pygame.display.set_caption("Conecta 4 - Reinicio 🎮")
dibujar_tablero(tablero)
pygame.display.update()

fuente = pygame.font.SysFont("arial", 45, bold=True)
#fuente para el contador
fuente_num_games = pygame.font.SysFont("arial", 25, bold=True)

columna_actual = COLUMN_COUNT // 2
ganador_texto = None

while True:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            sys.exit()

        # Movimiento de ficha con teclado
        if event.type == pygame.KEYDOWN:
            if not game_over:
                if event.key == pygame.K_LEFT:
                    columna_actual = max(0, columna_actual - 1)
                elif event.key == pygame.K_RIGHT:
                    columna_actual = min(COLUMN_COUNT - 1, columna_actual + 1)
                elif event.key == pygame.K_SPACE:
                    if movimiento_valido(tablero, columna_actual):
                        fila = siguiente_fila_vacia(tablero, columna_actual)
                        pieza = turno + 1
                        color_ficha = ROJO if turno == 0 else AMARILLO

                        animar_caida(columna_actual, fila, color_ficha)
                        soltar_pieza(tablero, fila, columna_actual, pieza)

                        if verificar_ganador(tablero, pieza):
                            ganador_texto = f"¡Jugador {pieza} gana!"
                            game_over = True

                        turno = (turno + 1) % 2
                        dibujar_tablero(tablero)

            # Reiniciar si el juego terminó y se presiona espacio
            elif event.key == pygame.K_SPACE:
                num_games = num_games + 1
                reiniciar_juego()

    # Dibujar ficha superior y mensaje de ganador
    pygame.draw.rect(screen, NEGRO, (0, 0, width, SQUARESIZE))
    
    #esto dibuja la letra de numero de partidas
    texto_partidas = fuente_num_games.render(f"Partidas jugadas: {num_games}", True, BLANCO)
    #AQUI DEBO REVISAR SI HAY FORMA DE HACER QUE EL TEXTO NO SE VAYA A CORRER MUCHO POR LA CANTIDAD DE PARTIDAS
    screen.blit(texto_partidas, (width - 300, 10))  

    if not game_over:
        color = ROJO if turno == 0 else AMARILLO
        pygame.draw.circle(screen, color, (int(columna_actual * SQUARESIZE + SQUARESIZE / 2), int(SQUARESIZE / 2)), RADIUS)
    else:
        texto = fuente.render(ganador_texto, True, ROJO if turno == 1 else AMARILLO)
        screen.blit(texto, (width / 2 - texto.get_width() / 2, 10))

        texto2 = pygame.font.SysFont("arial", 28).render("Presiona ESPACIO para jugar de nuevo", True, BLANCO)
        screen.blit(texto2, (width / 2 - texto2.get_width() / 2, 60))

        

    pygame.display.update()
