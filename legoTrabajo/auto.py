from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor
from pybricks.parameters import Port
from pybricks.tools import wait
import sys

# -----------------------------
# CONFIGURACIÓN DE MOTORES
# -----------------------------
hub = PrimeHub()

motorA = Motor(Port.A)   # Rueda derecha
motor_izq = Motor(Port.E)   # Rueda izquierda
motor_dir = Motor(Port.C)   # Dirección

# Variables iniciales
velocidad = 0
giro = 0

def aplicar_giro():
    """ Mueve el motor de dirección según el slider (-100 a 100). """
    motor_dir.run_target(300, giro)

def mover_adelante():
    motorA.dc(velocidad)
    motor_izq.dc(velocidad)

def mover_atras():
    motorA.dc(-velocidad)
    motor_izq.dc(-velocidad)

def detener():
    motorA.stop()
    motor_izq.stop()

# ----------------------------------------
# ENVÍA "rdy" PARA INDICAR QUE ESTÁ LISTO
# ----------------------------------------
def enviar_ready():
    # Añade un salto de línea para que el receptor basado en GATT pueda
    # recibir la notificación por líneas.
    sys.stdout.write("\x01rdy\n")
    sys.stdout.flush()

enviar_ready()

# ----------------------------------------
# BUCLE PRINCIPAL DE COMANDOS
# ----------------------------------------
while True:

    # Leer por línea en lugar de `read()` que bloquea hasta EOF.
    # Esto permite recibir comandos que el cliente BLE envía terminados
    # con un '\n'.
    cmd = sys.stdin.readline()

    if not cmd:
        wait(10)
        continue
    cmd = cmd.strip()

    # -----------------------------
    # COMANDOS DEL PC
    # Soporta múltiples formatos de comandos
    # -----------------------------
    if cmd in ["forward", "run_forward"]:
        mover_adelante()

    elif cmd in ["backward", "run_backward"]:
        mover_atras()

    elif cmd == "stop":
        detener()

    elif cmd.startswith("velocidad:"):
        velocidad = int(cmd.split(":")[1])

    elif cmd.startswith("giro:"):
        giro = int(cmd.split(":")[1])
        aplicar_giro()

    # Confirma recepción al PC
    enviar_ready()
