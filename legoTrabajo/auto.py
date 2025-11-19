from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor
from pybricks.parameters import Direction, Port
from pybricks.tools import wait

import sys

# -----------------------------
# CONFIGURACIÓN DE MOTORES
# -----------------------------
hub = PrimeHub()

motor_der = Motor(Port.A)   # Rueda derecha
motor_izq = Motor(Port.E)   # Rueda izquierda
motor_dir = Motor(Port.C)   # Dirección

# Variables iniciales
velocidad = 50
giro = 0

def aplicar_giro():
    """ Mueve el motor de dirección según el slider (-100 a 100). """
    motor_dir.run_target(300, giro)  # 300 = velocidad del motor de dirección

def mover_adelante():
    motor_der.dc(velocidad)
    motor_izq.dc(velocidad)

def mover_atras():
    motor_der.dc(-velocidad)
    motor_izq.dc(-velocidad)

def detener():
    motor_der.stop()
    motor_izq.stop()

# ----------------------------------------
# ENVÍA "rdy" para indicar que está listo
# ----------------------------------------
def enviar_ready():
    sys.stdout.buffer.write(b"\x01rdy")
    sys.stdout.buffer.flush()

enviar_ready()

# ----------------------------------------
# BUCLE PRINCIPAL DE COMANDOS
# ----------------------------------------
while True:
    data = sys.stdin.buffer.read(1)
    if not data:
        continue

    if data[0] != 6:
        continue  # Protocolo Pybricks: todos los comandos empiezan con 0x06

    cmd = sys.stdin.buffer.readline().decode().strip()

    # -----------------------------
    # COMANDOS RECIBIDOS DEL PC
    # -----------------------------
    if cmd == "forward":
        mover_adelante()

    elif cmd == "backward":
        mover_atras()

    elif cmd == "stop":
        detener()

    elif cmd.startswith("velocidad:"):
        velocidad = int(cmd.split(":")[1])
    
    elif cmd.startswith("giro:"):
        giro = int(cmd.split(":")[1])
        aplicar_giro()

    # Responde "rdy" para permitir el siguiente comando
    enviar_ready()
