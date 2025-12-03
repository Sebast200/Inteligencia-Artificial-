#td.py es el archivo que contiene las funciones necesarias para implementar
#el algoritmo de aprendizaje por diferencia temporal (TD) para el juego Conecta 4
#donde se define como aprende, como almacena estados y actualiza valores.
import os #para manejar archivos
import pickle #para guardar y cargar objetos
import random

#aqui es donde se importan funciones y variables del juego
from game import (
    ROW_COUNT,
    COLUMN_COUNT,
    movimiento_valido,
    siguiente_fila_vacia,
    tablero_lleno,
    verificar_ganador,
    J1,
    J2
)


#---------------------------------
# ruta correcta basada en este archivo
#---------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

#estos son los nombres de los archivos donde se guardan los valores y estadisticas
VALUES_FILE = os.path.join(BASE_DIR, "td_values.pkl")
STATS_FILE  = os.path.join(BASE_DIR, "td_stats.pkl")


#---configuraciones de TD(0)
#Alpha es la tasa de aprendizaje. determina cuanto ajusta el valor al aprender
ALPHA = 0.1
#Gamma es el descuento, determina la importancia de las recompensas futuras
GAMMA = 0.99
#Epsilon es la probabilidad de exploracion (jugar aleatorio en vez de mejor valor)
EPSILON = 0.20
#estos son los nombres de los archivos donde se guardan los valores y estadisticas


#---tabla de valores V(s) para los estados
#aqui es donde se almacenan los valores aproximados de cada estado
V = {} 

#esta es una lista con los estados que vio la IA aprendiz en una partida
episode_states = []


#---persistencia
#este metodo carga los valores de V desde un archivo, o inicia una nueva tabla si no existe
def cargar_valores():
    global V
    #si el archivo existe, lo abre y carga el diccionario V
    if os.path.exists(VALUES_FILE):
        with open(VALUES_FILE, "rb") as f:
            #carga el diccionario V usando pickle
            V = pickle.load(f)
    #en el caso contrario, inicia un diccionario vacio
    else:
        V = {}

#este metodo guarda los valores de V en un archivo para usarlos despues
def guardar_valores():
    #abre el archivo y guarda el diccionario V usando pickle
    with open(VALUES_FILE, "wb") as f:
        pickle.dump(V, f)


#---representacion de estados
#este metodo convierte el tablero en un string unico que sirve como key de diccionario.
def get_state_key(tablero, pieza):
    #el key incluye todos los valores del tablero (0,1,2) y la pieza del aprendiz TD
    flat = tablero.flatten().astype(int)
    return "".join(map(str, flat)) + f"_{pieza}"


#---Politica de selección de movimientos
#este metodo elige un movimiento usando la politica ε-greedy
def td_elegir_movimiento(tablero, pieza):
    #aqui se decide si explorar o explotar
    if random.random() < EPSILON:
        #con probabilidad epsilon, explora (hace un movimiento aleatorio)
        #lo que permite aprender nuevos estados
        valid = [c for c in range(COLUMN_COUNT) if movimiento_valido(tablero, c)]
        if not valid: return None, "bloqueado" # seguridad extra
        return random.choice(valid), "exploración"

    #en el caso de que no explore, explota (elige el mejor movimiento conocido)
    #aqui se inicializan las variables para encontrar el mejor movimiento
    best_value = -999999
    best_moves = [] # Lista para guardar los mejores movimientos (empates)
    decision = "explotación"
    
    #se revisan todas las columnas posibles
    for col in range(COLUMN_COUNT):
        #si el movimiento no es valido, se salta
        if not movimiento_valido(tablero, col):
            continue
        #en el caso de que sea valido, se simula el movimiento en una copia del tablero
        fila = siguiente_fila_vacia(tablero, col)
        copia = tablero.copy()
        copia[fila][col] = pieza
        #y calcula el valor del estado resultante
        key = get_state_key(copia, pieza)
        #obtiene el valor V(s) del estado resultante, si no existe en V, asume 0.0
        valor = V.get(key, 0.0)
        
        #--- Lógica de Desempate Aleatorio ---
        #si el valor es estrictamente mejor, reiniciamos la lista de mejores
        if valor > best_value:
            best_value = valor
            best_moves = [col]
        #si el valor es igual al mejor, lo añadimos a la lista
        elif valor == best_value:
            best_moves.append(col)
            
    #Si encontramos movimientos validos, elegimos uno al azar de los mejores
    if best_moves:
        best_col = random.choice(best_moves)
    else:
        #Fallback por seguridad (si no hubo moves validos o algo fallo)
        valid = [c for c in range(COLUMN_COUNT) if movimiento_valido(tablero, c)]
        if valid:
            best_col = random.choice(valid)
        else:
            return None, "empate/lleno"

    #retorna el mejor movimiento encontrado junto con el tipo de decision
    return best_col, decision


#---actualizacion TD(0)
#este metodo registra el estado actual del tablero para actualizarlo despues
def registrar_estado(tablero, pieza):
    #cada vez que la IA juega, se guarda el estado actual
    key = get_state_key(tablero, pieza)
    episode_states.append(key)

#este metodo actualiza los valores V usando el algoritmo TD(0)
def actualizar_td(resultado):
    #aqui se aplica la actualizacion TD(0) usando la ecuacion:
    #V(s) ← V(s) + α [ r + γ V(s') – V(s) ]

    #recompensa del final que se guarda en r:
    #1 es ganar, -1 es perder y 0 es empate
    r = resultado

    #recorremos los estados del episodio al reves
    for i in reversed(range(len(episode_states))):
        s = episode_states[i]

        #se obtiene el valor actual V(s)
        v_s = V.get(s, 0.0)

        #aqui se calcula el target r + γ V(s')
        if i == len(episode_states) - 1:
            #si es el ultimo estado, entonces no hay sucesor, y el target es la recompensa final
            target = r
        else:
            #sino, se obtiene el valor del siguiente estado V(s')
            s_next = episode_states[i + 1]
            target = r + GAMMA * V.get(s_next, 0.0)

        #se ajusta el valor hacia el target usando la tasa de aprendizaje α
        nuevo_valor = v_s + ALPHA * (target - v_s)
        V[s] = nuevo_valor

    #se limpia la memoria del episodio para la proxima partida.
    episode_states.clear()


#---resultado final
#este metodo obtiene la recompensa final para el aprendiz TD basada en el tablero final
def obtener_recompensa(tablero, pieza_td):
    #devuelve 1 si gana TD, -1 si pierde, 0 si empate
    ganador_td = verificar_ganador(tablero, pieza_td) is not None
    ganador_rival = verificar_ganador(tablero, J1 if pieza_td == J2 else J2) is not None

    if ganador_td:
        return 1
    if ganador_rival:
        return -1
    return 0